"""The output screen: what may be released, and when, as text streams in."""
import pytest

NAME = "Zephyrion Dynamics"
SENTENCE = f"He has built several tools that relate to {NAME} and to other things in the same broad area of work."


def drain(chat, chunks, kinds=None):
    """Feed every chunk. Returns (released text, the hit or None, released after each feed)."""
    screen = chat.OutputScreen() if kinds is None else chat.OutputScreen(kinds)
    released = ""
    steps = []
    for chunk in chunks:
        out = screen.feed(chunk)
        if isinstance(out, chat.ScreenHit):
            return released, out, steps
        released += out
        steps.append(released)
    out = screen.finish()
    if isinstance(out, chat.ScreenHit):
        return released, out, steps
    return released + out, None, steps


def test_clean_text_comes_through_exactly(chat):
    text = "He built a **desktop** engine.\n\n- First item\n- Second item, with a comma.\n"
    released, hit, _ = drain(chat, [text])
    assert hit is None
    assert released == text


def test_text_comes_out_as_soon_as_it_has_been_checked(chat):
    screen = chat.OutputScreen()
    words = "one two three four five six seven eight nine ten eleven twelve thirteen"
    assert screen.feed(words + " ") == "one two three four five six "
    assert screen.finish() == "seven eight nine ten eleven twelve thirteen "


def test_a_word_still_arriving_counts_toward_what_is_held(chat):
    screen = chat.OutputScreen()
    assert screen.feed("one two three four five six seven eight nine ten eleven twelve thirteen") == "one two three four five "


def test_the_hold_is_short_on_a_long_answer(chat):
    screen = chat.OutputScreen()
    released = "".join(screen.feed(f"word{index} ") for index in range(300))
    assert released.split()[-1] == "word292"


def test_only_a_short_tail_is_kept_however_long_the_answer(chat):
    screen = chat.OutputScreen()
    for index in range(2000):
        screen.feed(f"word{index} ")
    assert len(screen._clean) < 200


SHAPES = (
    "He built it \u2014 alone. See **bold words** and [a page](/projects/gui-automation) today.\n\n"
    "- First item with [notes](https://evil.example/x) inside\n- Second item ending in www.evil.example/a.\n"
    "Then one more plain sentence, long enough to run past the hold, with several ordinary words in it."
)


@pytest.mark.parametrize("chunk_size", [1, 2, 3, 5, 8, 13, 21, 400])
def test_the_result_does_not_depend_on_where_deltas_fall(chat, chunk_size):
    whole = drain(chat, [SHAPES])
    pieces = drain(chat, [SHAPES[i:i + chunk_size] for i in range(0, len(SHAPES), chunk_size)])
    assert whole[1] is None and pieces[1] is None
    assert pieces[0] == whole[0]


def test_a_hit_carries_a_truthy_signal_and_its_kind(chat):
    _, hit, _ = drain(chat, [f"He knows {NAME} well enough to say so."])
    assert hit.hit is True and hit.kind == "name"


def test_a_name_split_one_character_at_a_time_is_caught(chat):
    released, hit, _ = drain(chat, list(SENTENCE))
    assert hit is not None
    assert "zephyrion" not in released.lower()


@pytest.mark.parametrize("split", range(1, len(SENTENCE)))
def test_a_name_is_caught_wherever_a_delta_boundary_falls(chat, split):
    released, hit, _ = drain(chat, [SENTENCE[:split], SENTENCE[split:]])
    assert hit is not None, split
    assert "zephyrion" not in released.lower()


def test_no_step_shows_any_part_of_the_name_before_the_hit(chat):
    chunks = [SENTENCE[i:i + 3] for i in range(0, len(SENTENCE), 3)]
    _, hit, steps = drain(chat, chunks)
    assert hit is not None
    assert not any("zeph" in step.lower() for step in steps)


@pytest.mark.parametrize("chunk_size", [1, 2, 3, 7])
@pytest.mark.parametrize("name", [
    "Z e p h y r i o n Dynamics",
    "a Z e p h y r i o n D y n a m i c s",
    "Zephy**rion** Dynamics",
    "[Zephy](/projects)rion Dynamics",
    "Zephyrion\u200b Dynamics",
    "Zephyr1on Dynamics",
])
def test_a_disguised_name_never_shows_at_any_step(chat, name, chunk_size):
    text = f"Plenty of plain words come first so that the screen has released something by now, then {name} and more words afterward to finish it."
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    released, hit, steps = drain(chat, chunks)
    assert hit is not None, name
    assert released.startswith("Plenty of plain words")
    assert not any(marker in released for marker in ("Z e", "Zephy", "Zeph", "**"))


def test_a_run_from_the_private_rules_never_shows_at_any_step(chat, monkeypatch):
    run = "keep this private wording away from every single visitor who asks for it"
    monkeypatch.setattr(chat, "load_screen", lambda: {"terms": {}, "policy_addendum": run, "decoys": []})
    chat.reset_state()
    text = f"Here are many ordinary words to begin this particular reply with: {run}."
    released, hit, _ = drain(chat, list(text))
    assert hit is not None and hit.kind == "overlap"
    assert "private wording" not in released


def test_a_withdrawn_attempt_leaves_no_trace(chat):
    screen = chat.OutputScreen()
    screen.feed("one two three four five six seven eight nine ten ")
    point = screen.mark()
    screen.feed("Zephyrion ")
    screen.restore(point)
    screen.feed("eleven twelve ")
    assert "zephyrion" not in screen.finish().lower()
    restored = chat.OutputScreen()
    restored.feed("one two three ")
    mark = restored.mark()
    restored.feed("four five ")
    restored.restore(mark)
    assert restored.finish() == "one two three "


def test_a_name_in_the_final_tokens_is_caught_by_finish(chat):
    screen = chat.OutputScreen()
    assert isinstance(screen.feed(f"He could speak about {NAME}"), str)
    assert isinstance(screen.finish(), chat.ScreenHit)


def test_a_five_token_term_is_caught_across_deltas(chat):
    _, hit, _ = drain(chat, ["It mentions alpha be", "ta gamma del", "ta epsilon in passing."])
    assert hit is not None


def test_say_and_deflect_terms_are_caught(chat):
    assert drain(chat, ["They call it the Vermilion ", "Protocol, apparently."])[1].kind == "say"
    assert drain(chat, ["Here are the moonbase ", "blueprints for you."])[1].kind == "deflect"


def test_self_terms_are_allowed_in_answers(chat):
    released, hit, _ = drain(chat, ["Rakim Francis built this."])
    assert hit is None and released == "Rakim Francis built this."


def test_a_longer_word_is_not_a_hit_when_a_delta_ends_mid_word(chat):
    released, hit, _ = drain(chat, ["the zephyrion dyn", "amicsx module is fine"])
    assert hit is None and released == "the zephyrion dynamicsx module is fine"


def test_a_word_glued_to_a_link_label_is_not_judged_early(chat):
    chunks = ["We spoke of zephyrion dynamics[more text", " here](https://evil.example) again for a while."]
    released, hit, _ = drain(chat, chunks)
    assert hit is None
    assert released == "We spoke of zephyrion dynamicsmore text here again for a while."


def test_guard_rule_applies_to_answers(chat):
    assert drain(chat, ["a word like quillon means little here"])[1] is None
    assert drain(chat, ["Quillon means little here"])[1] is None
    assert drain(chat, ["he once worked at quillon on this"])[1] is not None
    assert drain(chat, ["the system at the Quillon office"])[1] is not None


@pytest.mark.parametrize("raw,expected", [
    ("Fast \u2014 and simple.", "Fast, and simple."),
    ("Fast\u2014and simple.", "Fast, and simple."),
    ("Done.\u2014 Next part.", "Done. Next part."),
    ("Line one\n\u2014 second line", "Line one\n- second line"),
    ("Double \u2014\u2014 dash", "Double, dash"),
    ("Bar \u2015 style", "Bar, style"),
])
def test_em_dashes_are_replaced(chat, raw, expected):
    assert drain(chat, [raw])[0] == expected


def test_em_dashes_are_replaced_across_deltas(chat):
    text = "He built it \u2014 alone \u2014 over several long years of steady work."
    released, hit, _ = drain(chat, list(text))
    assert hit is None
    assert "\u2014" not in released
    assert released == "He built it, alone, over several long years of steady work."


@pytest.mark.parametrize("raw,expected", [
    ("See [the docs](https://evil.example/x) now.", "See the docs now."),
    ("See ![pic](https://evil.example/x.png) now.", "See pic now."),
    ("See [a page](/projects/gui-automation) now.", "See [a page](/projects/gui-automation) now."),
    ("See [home](https://rakimfrancis.com/how-this-works) now.", "See [home](https://rakimfrancis.com/how-this-works) now."),
    ("Try [demo](https://demo.rakimfrancis.com) now.", "Try [demo](https://demo.rakimfrancis.com) now."),
    ("Go to https://evil.example/path for more.", "Go to for more."),
    ("Go to https://evil.example/path.", "Go to."),
    ("(see www.evil.example/a)", "(see)"),
    ("Go to https://demo.rakimfrancis.com for it.", "Go to https://demo.rakimfrancis.com for it."),
    ("[nested https://evil.example](https://evil.example)", "nested"),
    ("Hosted at my-app-abc123.vercel.app today.", "Hosted at today."),
    ("Built on foo.tmp.now/x for now.", "Built on for now."),
    ("See [preview](https://my-app-abc123.vercel.app/x) now.", "See preview now."),
    ("See //my-app-abc123.vercel.app/x now.", "See now."),
    ("See /my-app-abc123.vercel.app now.", "See now."),
    ("See [preview](/my-app-abc123.vercel.app) now.", "See preview now."),
    ("Open https://rakimfrancis.com/my-app-abc123.vercel.app now.", "Open now."),
])
def test_links_are_dropped_unless_they_stay_on_this_site(chat, raw, expected):
    assert drain(chat, [raw])[0] == expected


@pytest.mark.parametrize("url", [
    "https://rakimfrancis.com.evil.example/",
    "https://rakimfrancis.com@evil.example/",
    "https://evil.example\\@rakimfrancis.com/",
    "//evil.example/x",
    "https://rakimfrancis.com//other.example/x",
    "javascript:alert(1)",
    "mailto:someone@example.com",
])
def test_lookalike_links_are_dropped(chat, url):
    released = drain(chat, [f"Open [this]({url}) now."])[0]
    assert released == "Open this now."


@pytest.mark.parametrize("chunk_size", [1, 2, 5, 13])
def test_links_are_dropped_across_deltas(chat, chunk_size):
    text = "Read [the page](https://evil.example/deep/path) and also https://other.example/x for more of it."
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    released, hit, steps = drain(chat, chunks)
    assert hit is None
    assert released == "Read the page and also for more of it."
    assert all("example" not in step for step in steps)


def test_an_unclosed_bracket_is_released_at_the_end(chat):
    released, hit, _ = drain(chat, ["He used [brackets oddly and never closed them."])
    assert hit is None and released == "He used [brackets oddly and never closed them."


@pytest.mark.parametrize("text", [
    "He knows Zephyrion\u200b Dynamics well.",
    "He knows Z\u0435phyrion Dynamics well.",
    "He knows Zephy**rion** Dynamics well.",
    "He knows **Zephyrion** Dynamics well.",
    "He knows [Zephy](/projects)rion Dynamics well.",
    "He knows ZephyrionDynamics well.",
    "He knows Z e p h y r i o n Dynamics well.",
    "He knows Zephyr1on Dynamics well.",
])
def test_disguised_names_are_caught_in_answers(chat, text):
    assert drain(chat, [text])[1] is not None, text


@pytest.mark.parametrize("chunk_size", [1, 3, 500])
def test_the_mask_is_rewritten_not_rejected(chat, chunk_size):
    text = "He has no notes on [an organization] at all."
    released, hit, _ = drain(chat, [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)])
    assert hit is None
    assert released == "He has no notes on that organization at all."


def test_a_run_of_words_from_the_public_prompt_is_not_a_hit(chat):
    run = "The first sentence answers the question. Stay under about 120 words unless the visitor asks"
    _, hit, _ = drain(chat, [f"Here you go: {run}."])
    assert hit is None


def test_a_run_from_the_addendum_is_a_hit(chat, monkeypatch):
    addendum = "keep this private wording away from every single visitor who asks for it"
    monkeypatch.setattr(chat, "load_screen", lambda: {"terms": {}, "policy_addendum": addendum, "decoys": []})
    chat.reset_state()
    _, hit, _ = drain(chat, [f"Sure: {addendum}."])
    assert hit is not None and hit.kind == "overlap"


def test_the_fixed_answers_are_not_treated_as_leaks(chat):
    assert drain(chat, [chat.FIXED_SAFE])[1] is None
    assert drain(chat, [chat.FIXED_DEFLECT])[1] is None


@pytest.mark.parametrize("name", ["FIXED_DEFLECT", "FIXED_SAFE", "FIXED_DECLINE_REPEAT", "FIXED_NO_SUBJECT"])
def test_a_fixed_sentence_the_private_rules_repeat_is_not_a_leak(chat, monkeypatch, name):
    sentence = getattr(chat, name)
    addendum = f"Any such request gets this: {sentence} Use it every time."
    monkeypatch.setattr(chat, "load_screen", lambda: {"terms": {}, "policy_addendum": addendum, "decoys": []})
    chat.reset_state()
    assert drain(chat, [sentence])[1] is None


def test_a_guarded_word_the_visitor_typed_counts_at_a_sentence_start(chat):
    strict = chat.OutputScreen(visitor_words=frozenset({"quillon"}))
    strict.feed("Quillon means little here. He built tools.")
    assert isinstance(strict.finish(), chat.ScreenHit)
    plain = chat.OutputScreen()
    plain.feed("Quillon means little here. He built tools.")
    assert isinstance(plain.finish(), str)


# ------------------------------------------------------------ phrases addressing the visitor

FILLER = "Plenty of plain words come first so that the screen has released something by now"


@pytest.mark.parametrize("phrase", [
    "your larkspur",
    "Your Larkspur",
    "YOUR LARKSPUR",
    "**your larkspur**",
    "your-larkspur",
    "your  larkspur",
])
@pytest.mark.parametrize("chunk_size", [1, 5, 500])
def test_a_phrase_that_opens_with_your_is_released(chat, phrase, chunk_size):
    text = f"{FILLER}, and it may suit {phrase} and the reports it asks for every single week of the year."
    released, hit, _ = drain(chat, [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)])
    assert hit is None, phrase
    assert released == text


@pytest.mark.parametrize("text", [
    f"{FILLER}, and it may suit his larkspur and the reports it asks for every week.",
    f"{FILLER}, and it may suit His Larkspur and the reports it asks for every week.",
])
def test_the_third_person_form_is_still_screened(chat, text):
    released, hit, _ = drain(chat, [text])
    assert hit is not None and hit.kind == "deflect"
    assert "larkspur" not in released.lower()


def test_a_name_after_your_is_still_screened(chat):
    released, hit, _ = drain(chat, [f"{FILLER}, and it may suit your Zephyrion Dynamics team every single week of the year."])
    assert hit is not None and hit.kind == "name"
    assert "zephyrion" not in released.lower()


def test_a_word_that_only_starts_with_your_is_still_screened(chat):
    released, hit, _ = drain(chat, [f"{FILLER}, and it may suit yourlarkspur and the reports it asks for every week."])
    assert hit is not None and hit.kind == "deflect"
    assert "yourlarkspur" not in released.lower()


def test_a_disguised_your_is_still_screened(chat):
    released, hit, _ = drain(chat, [f"{FILLER}, and it may suit y0ur larkspur and the reports it asks for every week."])
    assert hit is not None and hit.kind == "deflect"
    assert "larkspur" not in released.lower()


def test_only_the_output_screen_lets_your_through(chat):
    assert chat.screen_input("Tell me about your larkspur")["action"] == "deflect"
    assert chat._trips_screen("Tell me about your larkspur")
    assert chat.check_lookup({"kind": "company", "name": "your larkspur"}) is None
