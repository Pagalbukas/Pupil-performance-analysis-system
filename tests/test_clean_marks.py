from analyser.models import Mark

def test_raw_int_mark():
    assert Mark(1).clean == 1

def test_raw_int_0_mark():
    assert Mark(0).clean is None

def test_raw_float_0_mark():
    assert Mark(0.0).clean is None

def test_raw_float_mark():
    assert Mark(1.1).clean == 1.1

def test_raw_none_mark():
    assert Mark(None).clean is None

def test_raw_string_int_mark():
    assert Mark("1").clean == 1

def test_raw_string_float_mark():
    assert Mark("1.1").clean == 1.1

def test_raw_string_special_program_int_mark1():
    assert Mark("9IN").clean == 9

def test_raw_string_special_program_int_mark2():
    assert Mark("9PR").clean == 9

def test_raw_string_special_program_float_mark1():
    assert Mark("9.7IN").clean == 9.7

def test_raw_string_special_program_float_mark2():
    assert Mark("9.7PR").clean == 9.7

def test_raw_string_passed_mark():
    assert Mark("įsk").clean is True

def test_raw_string_special_program_passed_mark1():
    assert Mark("įskIN").clean is True

def test_raw_string_special_program_passed_mark2():
    assert Mark("įskPR").clean is True

def test_raw_string_not_passed_mark():
    assert Mark("nsk").clean is False

def test_raw_string_special_program_not_passed_mark1():
    assert Mark("nskIN").clean is False

def test_raw_string_special_program_not_passed_mark2():
    assert Mark("nskPR").clean is False

def test_raw_string_0_mark():
    assert Mark("0").clean is None

def test_raw_string_0point0_mark():
    assert Mark("0.0").clean is None

def test_raw_string_special_program_0_mark1():
    assert Mark("0IN").clean is None

def test_raw_string_special_program_0_mark2():
    assert Mark("0PR").clean is None

def test_raw_string_hour_mark():
    assert Mark("4 val.").clean is None

def test_raw_string_hyphen_mark():
    assert Mark("-").clean is None

def test_raw_string_exempt_mark():
    assert Mark("atl").clean is None
