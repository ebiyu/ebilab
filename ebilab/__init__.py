
class VersionDidNotMatch(Exception):
    pass

def assert_ebilab_version(want: str):
    """
    This raises the VersionDidNotMatch exception if versison did not match.
    If the version of package is "dev", this always raise the exception
    """
    import pkg_resources
    got = pkg_resources.require("ebilab")[0].version
    if got == "dev":
        raise VersionDidNotMatch("Current version of ebilab is 'dev'")
    got_list = got.split(".")
    want_list = want.split(".")
    cnt = len(want_list)
    for i in range(cnt):
        if got_list[i] != want_list[i]:
            raise VersionDidNotMatch(f"Version did not match: current {got}, required {want}")

