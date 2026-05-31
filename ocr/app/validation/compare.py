

def fuzzy_compare(str1, str2, threshold=FUZZY_MATCH_THRESHOLD):
    """
    Compare two strings with fuzzy matching.
    Returns: (similarity_score, is_match)
    """
    if not str1 or not str2:
        return (0, False)

    str1 = str(str1).strip().lower()
    str2 = str(str2).strip().lower()

    if str1 == str2:
        return (100, True)

    similarity = fuzz.token_set_ratio(str1, str2)
    is_match = similarity >= threshold

    return (similarity, is_match)


def strict_compare(val1, val2, tolerance=STRICT_NUMERIC_TOLERANCE):
    """
    Compare numbers strictly.
    Returns: (match_bool, difference)
    """
    if val1 is None or val2 is None:
        return (False, None)

    try:
        v1 = float(val1)
        v2 = float(val2)
        diff = abs(v1 - v2)

        # Allow small tolerance for floating point
        is_match = (diff <= tolerance)

        return (is_match, diff)

    except:
        return (False, None)
