from app.ingestion.importers.base import DataSourceImporter


class FAASDRImporter(DataSourceImporter):
    source_name = 'FAA_SDR'
    base_url = 'https://drs.faa.gov'
    search_endpoint = '/browse/excelExternalWindow/'
    request_timeout_seconds = 30
    target_manufacturers = ('BOEING', 'AIRBUS')
