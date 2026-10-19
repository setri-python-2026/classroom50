"""Autograder checks for the innlating assignments.

Published in each assignment's Classroom 50 bundle and run from the
student's checkout as:

    python3 "$CLASSROOM50_BUNDLE_DIR/check.py" <check> [file]

Exit code 0 means PASS. Messages are printed for the student.
"""
import ast
import contextlib
import io
import random
import re
import runpy
import sys
from typing import NoReturn


def fail(message) -> NoReturn:
    print(f"FAIL: {message}")
    sys.exit(1)


def ok(message) -> NoReturn:
    print(f"OK: {message}")
    sys.exit(0)


def parse(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return ast.parse(fh.read(), filename=path)
    except FileNotFoundError:
        fail(f"{path} not found (check the file name)")
    except SyntaxError as exc:
        fail(f"{path} has a syntax error on line {exc.lineno}: {exc.msg}")


def patch_random():
    """Make random predictable: always pick the second-lowest value.

    randint(1, 1000), randrange(1, 1001) and randrange(1000) + 1 all give 2,
    so a guess-the-number game always hides the number 2.
    """
    def randrange(start, stop=None, step=1):
        if stop is None:
            start, stop = 0, start
        return start + step if start + step < stop else start

    random.randrange = randrange
    random.randint = lambda a, b: a + 1 if a < b else a
    random.choice = lambda seq: seq[1] if len(seq) > 1 else seq[0]
    random.random = lambda: 0.001
    random.uniform = lambda a, b: a
    random.shuffle = lambda seq, *args: None


def run(path, stdin="", fixed_random=False):
    """Run a student script in-process; return (stdout, globals, error)."""
    parse(path)
    if fixed_random:
        patch_random()
    out = io.StringIO()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin)
    namespace, error = {}, None
    try:
        with contextlib.redirect_stdout(out):
            namespace = runpy.run_path(path, run_name="__main__")
    except (EOFError, SystemExit, KeyboardInterrupt):
        pass  # ran out of input, or the script called exit()
    except Exception as exc:  # noqa: BLE001 - report any crash to the student
        error = exc
    finally:
        sys.stdin = old_stdin
    return out.getvalue(), namespace, error


def has_loop_in_loop(tree, outer, inner):
    for node in ast.walk(tree):
        if isinstance(node, outer):
            for child in ast.walk(node):
                if child is not node and isinstance(child, inner):
                    return True
    return False


def imports(tree, module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] == module for a in node.names):
                return True
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] == module:
                return True
    return False


# --- innlating-2 -----------------------------------------------------------

def triangles(path):
    output, _, error = run(path)
    if error:
        fail(f"{path} crashed: {error!r}")
    rows = [line for line in output.splitlines() if "*" in line]
    if len(rows) != 10:
        fail(f"expected 10 rows of asterisks, found {len(rows)}")
    spans = []
    for n, line in enumerate(rows, start=1):
        groups = list(re.finditer(r"\*+", line.expandtabs()))
        expected = [n, 11 - n, 11 - n, n]
        if [len(g.group()) for g in groups] != expected:
            fail(f"row {n}: expected triangles of {expected} asterisks, "
                 f"found {[len(g.group()) for g in groups]}")
        spans.append([g.span() for g in groups])
    # Triangles 1 and 2 are left-aligned, 3 and 4 right-aligned.
    for t, (edge, side) in enumerate(((0, "left"), (0, "left"),
                                      (1, "right"), (1, "right")), start=1):
        if len({row[t - 1][edge] for row in spans}) != 1:
            fail(f"triangle {t} should be {side}-aligned")
    ok("four triangles side by side")


def nested_for(path):
    if has_loop_in_loop(parse(path), ast.For, ast.For):
        ok("uses nested for loops")
    fail(f"{path} must use nested for loops")


def uses_while(path):
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.While):
            ok("uses a while loop")
    fail(f"{path} must use a while loop")


# --- innlating-3 -----------------------------------------------------------

def guess_game(path):
    # The hidden number is 2: guess too low, too high, then correct.
    output, _, _ = run(path, "1\n3\n2\nno\nn\n0\nq\n", fixed_random=True)
    text = output.lower()
    for phrase in ("too low", "too high", "congratulations"):
        if phrase not in text:
            fail(f"guessing 1, 3 and then 2 (the hidden number) never "
                 f"printed '{phrase}'")
    ok("hints and congratulations shown")


def guess_again(path):
    # Win, say yes to another game, win again, then quit.
    for yes in ("yes", "y", "1"):
        output, _, _ = run(path, f"2\n{yes}\n2\nno\nn\n0\nq\n",
                           fixed_random=True)
        if output.lower().count("congratulations") >= 2:
            ok("the player can choose to play again")
    fail("after winning and answering yes/y to playing again, a second "
         "game could not be won")


RESPONSES = ("very good", "nice work", "keep up the good work", "excellent",
             "no. please try again", "wrong. try once more", "no. keep trying",
             "don't give up")


def cai(path):
    # Answer "1" to every prompt (difficulty, operation, answers).
    output, _, error = run(path, "1\n" * 60, fixed_random=True)
    text = output.lower()
    if "how much is" not in text:
        fail(f"no 'How much is ...' question was asked"
             + (f" ({path} crashed: {error!r})" if error else ""))
    if not any(r in text for r in RESPONSES):
        fail("answers got none of the responses from the assignment")
    ok("asks questions and responds to answers")


# --- innlating-4 -----------------------------------------------------------

def is_prime(n):
    return n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))


def sieve(path):
    _, namespace, error = run(path)
    if error:
        fail(f"{path} crashed: {error!r}")
    primes = namespace.get("primes")
    if not isinstance(primes, list) or len(primes) != 1000:
        fail("expected a 1000-element list named 'primes'")
    for i in range(2, 1000):
        if bool(primes[i]) != is_prime(i):
            fail(f"primes[{i}] is {primes[i]}, but {i} is "
                 f"{'' if is_prime(i) else 'not '}a prime")
    ok("primes[i] is True exactly for the primes below 1000")


FACES = ("Ace|Deuce|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Jack|Queen"
         "|King")
CARD = re.compile(rf"\b({FACES}) of (Hearts|Diamonds|Clubs|Spades)\b")


def deal(path):
    output, _, error = run(path)
    if error:
        fail(f"{path} crashed: {error!r}")
    return output


def cards(path):
    output = deal(path)
    found = CARD.findall(output)
    if len(found) != 52 or len(set(found)) != 52:
        fail(f"expected 52 different cards like 'Ace of Hearts', found "
             f"{len(set(found))} different out of {len(found)}")
    rows = [CARD.findall(line) for line in output.splitlines()]
    rows = [r for r in rows if r]
    if [len(r) for r in rows] != [4] * 13:
        fail("expected 13 rows of 4 cards")
    ok("all 52 cards in four columns")


def shuffled(path):
    if deal(path) == deal(path):
        fail("two runs printed the same order; is the deck shuffled?")
    ok("the deck is shuffled")


def has_function(path, name):
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            ok(f"defines {name}()")
    fail(f"{path} must define a function named {name}")


def craps_dicts(path):
    _, namespace, error = run(path)
    if error:
        fail(f"{path} crashed: {error!r}")
    wins, losses = namespace.get("wins"), namespace.get("losses")
    if not isinstance(wins, dict) or not isinstance(losses, dict):
        fail("expected dictionaries named 'wins' and 'losses'")
    total = sum(wins.values()) + sum(losses.values())
    if total != 1_000_000:
        fail(f"wins and losses add up to {total} games, not 1000000")
    ok("wins and losses cover 1000000 games")


def craps_summary(path):
    output, _, error = run(path)
    if error:
        fail(f"{path} crashed: {error!r}")
    percents = [float(p) for p in re.findall(r"(\d+(?:\.\d+)?)\s*%", output)]
    checks = (("winning percentage (about 49.3%)", 48.8, 49.8),
              ("losing percentage (about 50.7%)", 50.2, 51.2),
              ("cumulative 100%", 99.9, 100.1))
    for label, low, high in checks:
        if not any(low <= p <= high for p in percents):
            fail(f"no {label} found in the summary")
    ok("summary shows win/loss percentages and reaches 100%")


# --- innlating-5 -----------------------------------------------------------

def uses_numpy(*paths):
    for path in paths:
        if not imports(parse(path), "numpy"):
            fail(f"{path} must use numpy")
    ok("numpy is used")


CHECKS = {
    "triangles": triangles,
    "nested-for": nested_for,
    "uses-while": uses_while,
    "guess-game": guess_game,
    "guess-again": guess_again,
    "cai": cai,
    "sieve": sieve,
    "cards": cards,
    "shuffled": shuffled,
    "initialize-deck": lambda p: has_function(p, "initialize_deck"),
    "craps-dicts": craps_dicts,
    "craps-summary": craps_summary,
    "uses-numpy": uses_numpy,
}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in CHECKS:
        sys.exit(f"usage: check.py {{{'|'.join(CHECKS)}}} FILE...")
    CHECKS[sys.argv[1]](*sys.argv[2:])
