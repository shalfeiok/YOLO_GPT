from app.application.container import Container


def test_job_runner_initializes_job_registry_before_submit() -> None:
    container = Container()

    def _quick_job(_token, progress):
        progress(1.0, "done")
        return 42

    handle = container.job_runner.submit("quick", _quick_job)
    assert handle.future.result(timeout=2) == 42

    records = container.job_registry.list()
    assert records
    assert records[0].name == "quick"
    assert records[0].status == "finished"
