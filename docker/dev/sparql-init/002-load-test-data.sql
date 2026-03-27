-- Load test data exported from the https://data.4tu.nl graph
-- into the djehuty://local graph used by the application.
-- The data is split into multiple files to stay under GitHub's 100MB file size limit.
DB.DBA.TTLP_MT(file_to_string_output('/initdb.d/data-part-1.nt'), '', 'djehuty://local', 255);
DB.DBA.TTLP_MT(file_to_string_output('/initdb.d/data-part-2.nt'), '', 'djehuty://local', 255);
DB.DBA.TTLP_MT(file_to_string_output('/initdb.d/data-part-3.nt'), '', 'djehuty://local', 255);
DB.DBA.TTLP_MT(file_to_string_output('/initdb.d/data-part-4.nt'), '', 'djehuty://local', 255);
DB.DBA.TTLP_MT(file_to_string_output('/initdb.d/data-part-5.nt'), '', 'djehuty://local', 255);
