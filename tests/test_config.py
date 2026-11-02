from faultline.config import tracked_repos


def test_tracked_repos_file_is_nonempty_and_lowercase():
    repos = tracked_repos()
    assert len(repos) > 1000
    assert all(r == r.lower() for r in repos)
