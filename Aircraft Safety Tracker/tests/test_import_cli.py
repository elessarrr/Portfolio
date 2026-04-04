def test_import_data_cli_exists(runner):
    result = runner.invoke(args=['import-data', '--help'])
    assert result.exit_code == 0
    assert 'Commands:' in result.output


def test_import_data_ntsb_command_runs(runner):
    result = runner.invoke(args=['import-data', 'ntsb', '--start-date', '2020-01-01', '--end-date', '2020-01-02'])
    assert result.exit_code == 0


def test_import_data_all_continues_after_source_failure(app, runner, monkeypatch):
    with app.app_context():
        import app.ingestion.cli as ingestion_cli

        original_run = ingestion_cli.NoopImporter.run

        def failing_run(self):
            if self.source_name == 'NTSB':
                raise RuntimeError('boom')
            return original_run(self)

        monkeypatch.setattr(ingestion_cli.NoopImporter, 'run', failing_run)
        result = runner.invoke(args=['import-data', 'all', '--incremental'])
        assert result.exit_code != 0


def test_seed_jasc_command_inserts_mappings(app, runner):
    with app.app_context():
        result = runner.invoke(args=['import-data', 'seed-jasc'])
        assert result.exit_code == 0
