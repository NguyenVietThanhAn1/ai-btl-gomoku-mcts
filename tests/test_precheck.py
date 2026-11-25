from gameai.tools import precheck as pc


def _run(codes: list[int]):
    steps = [(f"s{i}", ["x", str(i)]) for i in range(len(codes))]
    lines: list[str] = []
    seen: list[str] = []

    def runner(cmd):
        i = int(cmd[1])
        seen.append(cmd[1])
        return codes[i], f"out {i}\n" * 3

    rc = pc.precheck(steps, runner, tail=2, out=lines.append)
    return rc, seen, "\n".join(lines)


def test_all_pass_returns_zero():
    rc, seen, text = _run([0, 0, 0])
    assert rc == 0 and seen == ["0", "1", "2"]
    assert "3/3 PASS" in text and "FAIL" not in text


def test_any_failure_returns_nonzero_and_runs_all_steps():
    rc, seen, text = _run([0, 3, 0])
    assert rc == 1 and seen == ["0", "1", "2"]  # không dừng ở lỗi đầu
    assert "[FAIL] s1" in text and "2/3 PASS" in text and "FAIL: s1" in text
    assert text.count("    out 1") == 2  # in đuôi `tail` dòng của bước lỗi


def test_real_steps_cover_required_checks():
    joined = [" ".join(c[1:]) for _, c in pc.STEPS]
    assert joined == [
        "-m pytest -q",
        "-m ruff check .",
        "-m ruff format --check .",
        "-m gameai.experiments.report_check",
        "-m gameai.experiments.plots --check",
    ]


def test_run_command_returns_real_exit_code():
    code, text = pc.run_command([pc.PY, "-c", "import sys; print('hi'); sys.exit(7)"])
    assert code == 7 and "hi" in text
