"""
Search & discovery tests.

Covers:
    - Perform keyword search from homepage search bar
    - Apply filters (institution, deposit type, file format, date range, license, category)
    - Verify sort options work (date, title)
    - Navigate category browser and category detail pages
    - Navigate institution pages

These tests create their own published dataset to ensure search results exist.

Run with:
    cd e2e && python -m pytest tests/test_search.py -v
"""

import pytest
from pathlib import Path
from playwright.sync_api import Page, expect

from config import BASE_URL
from helpers.dataset import create_draft_dataset, get_container_uuid_from_url
from helpers.publish import fill_required_fields_and_publish
from pages.dataset_editor_page import DatasetEditorPage
from pages.search_page import SearchPage


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

SEARCH_DATASET_TITLE = "Search Test Dataset For Discovery"
TEST_FILE_CONTENT = b"Search test file content.\n"
TEST_FILE_NAME = "search-test-file.txt"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_file(tmp_path: Path) -> str:
    """Create a temporary test file and return its path."""
    file_path = tmp_path / TEST_FILE_NAME
    file_path.write_bytes(TEST_FILE_CONTENT)
    return str(file_path)


@pytest.fixture()
def searchable_dataset(authenticated_page: Page, test_file: str):
    """Create and publish a dataset so that search has at least one result.

    Returns the authenticated page after re-login.
    """
    url = create_draft_dataset(authenticated_page)
    container_uuid = get_container_uuid_from_url(url)
    editor = DatasetEditorPage(authenticated_page)
    editor.wait_for_ready()
    editor.upload_file(test_file)
    editor.save()

    fill_required_fields_and_publish(
        authenticated_page,
        container_uuid,
        title=SEARCH_DATASET_TITLE,
        description="<p>A dataset created for search and discovery E2E tests.</p>",
    )

    # Re-login after publish (review flow changes session state)
    authenticated_page.goto("/login")
    authenticated_page.wait_for_url("**/my/dashboard**")

    # Wait for the dataset to appear on the public page
    authenticated_page.goto(f"/datasets/{container_uuid}")
    authenticated_page.wait_for_load_state("domcontentloaded")

    return authenticated_page


# ---------------------------------------------------------------------------
# Search from homepage
# ---------------------------------------------------------------------------


@pytest.mark.search
class TestKeywordSearch:
    """Test searching via the header search bar."""

    def test_search_from_homepage(self, searchable_dataset, page: Page, screenshot):
        """Typing a query in the homepage search bar should navigate to /search."""
        page.goto("/portal")
        screenshot(page, "portal-before-search")

        search = SearchPage(page)
        search.search_from_header("Search Test")
        screenshot(page, "search-results-page")

        expect(page).to_have_url(f"{BASE_URL}/search?search=Search+Test")

    def test_search_returns_results(self, searchable_dataset, page: Page, screenshot):
        """A broad search term should return at least one result."""
        search = SearchPage(page)
        search.navigate("/search?search=Search+Test+Dataset")
        search.wait_for_results()
        screenshot(page, "search-results-loaded")

        count = search.get_tile_count()
        assert count > 0, "Expected at least one search result"

    def test_search_result_count_displayed(self, searchable_dataset, page: Page, screenshot):
        """The result count badge should show a non-empty value."""
        search = SearchPage(page)
        search.navigate("/search?search=Search+Test+Dataset")
        search.wait_for_results()
        screenshot(page, "result-count")

        count_text = search.get_result_count_text()
        assert count_text != "", "Expected result count to be displayed"

    def test_empty_search_returns_all(self, searchable_dataset, page: Page, screenshot):
        """An empty search term should show results (all items)."""
        search = SearchPage(page)
        search.navigate("/search")
        search.wait_for_results()
        screenshot(page, "all-results")

        count = search.get_tile_count()
        assert count > 0, "Expected results for empty search"

    def test_search_no_results(self, page: Page, screenshot):
        """A nonsensical query should return zero results."""
        search = SearchPage(page)
        search.navigate("/search?search=zzzzxqxqxq999nonexistent")
        # Wait for loader to finish
        page.locator("#search-loader").wait_for(state="hidden", timeout=15000)
        page.wait_for_timeout(1000)
        screenshot(page, "no-results")

        count = search.get_tile_count()
        assert count == 0, "Expected no results for nonsensical query"


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


@pytest.mark.search
class TestSearchFilters:
    """Test search filter sidebar controls."""

    def test_deposit_type_filter(self, searchable_dataset, page: Page, screenshot):
        """Checking 'Dataset' deposit type and applying should filter results."""
        search = SearchPage(page)
        search.navigate("/search")
        search.wait_for_results()
        screenshot(page, "before-filter")

        search.check_filter("checkbox_datatypes_3")
        search.apply_filters()
        search.wait_for_results()
        screenshot(page, "after-dataset-filter")

        # Results should still load (may be same or fewer)
        expect(page.locator("#search-results-tile-view")).to_be_visible()

    def test_published_date_filter(self, searchable_dataset, page: Page, screenshot):
        """Checking a published date filter and applying should work."""
        search = SearchPage(page)
        search.navigate("/search")
        search.wait_for_results()

        search.check_filter("checkbox_publisheddate_3")
        search.apply_filters()
        search.wait_for_results()
        screenshot(page, "after-date-filter")

        expect(page.locator("#search-results-tile-view")).to_be_visible()

    def test_search_scope_filter(self, searchable_dataset, page: Page, screenshot):
        """Applying a search scope filter (title only) should work."""
        search = SearchPage(page)
        search.navigate("/search?search=Search+Test")
        search.wait_for_results()

        search.check_filter("checkbox_searchscope_title")
        search.apply_filters()
        search.wait_for_results()
        screenshot(page, "after-scope-filter")

        expect(page.locator("#search-results-tile-view")).to_be_visible()

    def test_reset_filters(self, searchable_dataset, page: Page, screenshot):
        """The reset button should clear all filters."""
        search = SearchPage(page)
        search.navigate("/search")
        search.wait_for_results()

        # Apply a filter first
        search.check_filter("checkbox_datatypes_9")
        search.apply_filters()
        search.wait_for_results()
        screenshot(page, "filter-applied")

        # Reset
        search.reset_filters()
        search.wait_for_results()
        screenshot(page, "filters-reset")

        # The checkbox should be unchecked
        checkbox = page.locator("#checkbox_datatypes_9")
        expect(checkbox).not_to_be_checked()

    def test_filter_apply_button_exists(self, page: Page, screenshot):
        """The Apply and Reset filter buttons should be present."""
        search = SearchPage(page)
        search.navigate("/search")
        screenshot(page, "filter-buttons")

        expect(page.locator("#search-filter-apply-button")).to_be_visible()
        expect(page.locator("#search-filter-reset-button")).to_be_visible()

    def test_filter_sections_present(self, page: Page, screenshot):
        """All filter sections should be present on the search page."""
        search = SearchPage(page)
        search.navigate("/search")
        screenshot(page, "filter-sections")

        for section_id in [
            "search-filter-content-institutions",
            "search-filter-content-datatypes",
            "search-filter-content-searchscope",
            "search-filter-content-filetypes",
            "search-filter-content-publisheddate",
            "search-filter-content-licenses",
            "search-filter-content-categories",
        ]:
            expect(page.locator(f"#{section_id}")).to_be_visible()


# ---------------------------------------------------------------------------
# Sort options
# ---------------------------------------------------------------------------


@pytest.mark.search
class TestSearchSort:
    """Test sort dropdown options on the search page."""

    def test_sort_dropdown_present(self, page: Page, screenshot):
        """The sort dropdown should be visible with expected options."""
        search = SearchPage(page)
        search.navigate("/search")
        screenshot(page, "sort-dropdown")

        sort_select = page.locator("#sort-by")
        expect(sort_select).to_be_visible()

        options = sort_select.locator("option")
        assert options.count() == 4

    def test_sort_by_date_old_first(self, searchable_dataset, page: Page, screenshot):
        """Selecting 'Date (Old First)' should reload results."""
        search = SearchPage(page)
        search.navigate("/search")
        search.wait_for_results()

        search.select_sort("date_asc")
        search.wait_for_results()
        screenshot(page, "sorted-date-asc")

        assert search.get_tile_count() > 0

    def test_sort_by_title_az(self, searchable_dataset, page: Page, screenshot):
        """Selecting 'Title (A to Z)' should reload results."""
        search = SearchPage(page)
        search.navigate("/search")
        search.wait_for_results()

        search.select_sort("title_asc")
        search.wait_for_results()
        screenshot(page, "sorted-title-asc")

        assert search.get_tile_count() > 0

    def test_default_sort_is_date_new_first(self, page: Page, screenshot):
        """The default selected sort option should be 'Date (New First)'."""
        search = SearchPage(page)
        search.navigate("/search")
        screenshot(page, "default-sort")

        selected = page.locator("#sort-by").input_value()
        assert selected == "date_dsc"


# ---------------------------------------------------------------------------
# View modes
# ---------------------------------------------------------------------------


@pytest.mark.search
class TestSearchViewMode:
    """Test tile and list view switching."""

    def test_switch_to_list_view(self, searchable_dataset, page: Page, screenshot):
        """Clicking list view mode should display results in a table."""
        search = SearchPage(page)
        search.navigate("/search")
        search.wait_for_results()
        screenshot(page, "tile-view")

        search.switch_to_list_view()
        page.wait_for_timeout(500)
        screenshot(page, "list-view")

        expect(page.locator("#search-results-list-view")).to_be_visible()

    def test_switch_back_to_tile_view(self, searchable_dataset, page: Page, screenshot):
        """Switching to list and back to tile view should work."""
        search = SearchPage(page)
        search.navigate("/search")
        search.wait_for_results()

        search.switch_to_list_view()
        page.wait_for_timeout(500)
        search.switch_to_tile_view()
        page.wait_for_timeout(500)
        screenshot(page, "back-to-tile-view")

        expect(page.locator("#search-results-tile-view")).to_be_visible()


# ---------------------------------------------------------------------------
# Category browser
# ---------------------------------------------------------------------------


@pytest.mark.search
class TestCategoryBrowser:
    """Test category listing and detail pages."""

    def test_category_listing_page_loads(self, page: Page, screenshot):
        """The /category page should load with category headings."""
        response = page.goto("/category", wait_until="commit", timeout=60000)
        assert response is not None
        assert response.status == 200
        screenshot(page, "category-listing")

        expect(page.locator("h1")).to_contain_text("Overview")

    def test_category_detail_page_loads(self, page: Page, screenshot):
        """A category detail page (/categories/<id>) should load successfully."""
        response = page.goto("/categories/13431")
        assert response is not None
        assert response.status == 200
        screenshot(page, "category-detail-mathematics")

        expect(page.locator("h1")).to_contain_text("Mathematical Sciences")

    def test_category_detail_has_sections(self, page: Page, screenshot):
        """A category detail page should have top datasets and latest datasets."""
        page.goto("/categories/13431")
        page.wait_for_load_state("domcontentloaded")
        screenshot(page, "category-sections")

        expect(page.locator("#top-buttons")).to_be_visible()
        expect(page.locator("#top-datasets")).to_be_visible()

    def test_category_top_tabs(self, page: Page, screenshot):
        """The top datasets section should have Downloads, Views, Shares, Citations tabs."""
        page.goto("/categories/13431")
        page.wait_for_load_state("domcontentloaded")
        screenshot(page, "category-top-tabs")

        tabs = page.locator("#top-buttons ul li")
        assert tabs.count() == 4
        expect(tabs.nth(0)).to_contain_text("Downloads")
        expect(tabs.nth(1)).to_contain_text("Views")
        expect(tabs.nth(2)).to_contain_text("Shares")
        expect(tabs.nth(3)).to_contain_text("Citations")

    def test_category_listing_links_to_details(self, page: Page, screenshot):
        """The category listing page should link to individual category pages."""
        page.goto("/category", wait_until="commit", timeout=60000)
        page.wait_for_load_state("domcontentloaded")

        detail_link = page.locator("a[href*='/categories/']").first
        expect(detail_link).to_be_visible()
        screenshot(page, "category-listing-links")


# ---------------------------------------------------------------------------
# Institution pages
# ---------------------------------------------------------------------------


@pytest.mark.search
class TestInstitutionPages:
    """Test institution listing and detail pages."""

    def test_institution_page_loads(self, page: Page, screenshot):
        """An institution page should load successfully."""
        response = page.goto("/institutions/Delft_University_of_Technology")
        assert response is not None
        assert response.status == 200
        screenshot(page, "institution-tudelft")

        expect(page.locator("#top-buttons")).to_be_visible()

    def test_institution_has_top_datasets(self, page: Page, screenshot):
        """An institution page should have a top datasets section."""
        page.goto("/institutions/Delft_University_of_Technology")
        page.wait_for_load_state("domcontentloaded")
        screenshot(page, "institution-top-datasets")

        expect(page.locator("#top-buttons")).to_be_visible()
        expect(page.locator("#top-datasets")).to_be_visible()

    def test_institution_has_latest_datasets(self, page: Page, screenshot):
        """An institution page should have a latest datasets section."""
        page.goto("/institutions/Delft_University_of_Technology")
        page.wait_for_load_state("domcontentloaded")
        screenshot(page, "institution-latest-datasets")

        expect(page.get_by_role("heading", name="Latest datasets")).to_be_visible()

    def test_multiple_institutions_accessible(self, page: Page, screenshot):
        """All configured institutions should be accessible."""
        institutions = [
            "Delft_University_of_Technology",
            "University_of_Twente",
            "Eindhoven_University_of_Technology",
            "Wageningen_University_and_Research",
        ]
        for inst in institutions:
            response = page.goto(f"/institutions/{inst}")
            assert response is not None
            assert response.status == 200, f"Institution {inst} returned {response.status}"

        screenshot(page, "last-institution-page")

    def test_institution_top_tabs(self, page: Page, screenshot):
        """An institution page top section should have the ranking tabs."""
        page.goto("/institutions/Delft_University_of_Technology")
        page.wait_for_load_state("domcontentloaded")
        screenshot(page, "institution-top-tabs")

        tabs = page.locator("#top-buttons ul li")
        assert tabs.count() == 4
        expect(tabs.nth(0)).to_contain_text("Downloads")
        expect(tabs.nth(1)).to_contain_text("Views")
