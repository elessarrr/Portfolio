from app.ingestion.link_schema import merge_links_into_source_data, normalize_link_entry


def test_merge_links_dedupes_urls():
    data = merge_links_into_source_data(
        {"links": [normalize_link_entry(url="https://a.example", role="primary")]},
        [normalize_link_entry(url="https://a.example", role="docket")],
    )
    assert len(data["links"]) == 1
