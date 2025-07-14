def cons(ary):
    for i in range(len(ary) - 1):
        yield (ary[i], ary[i + 1])


def get_rise_and_fall(profile):
    rise = 0
    fall = 0

    if profile is not None:
        for (d1, e1), (d2, e2) in cons(profile):
            diff = e2 - e1
            if diff > 0:
                rise += diff
            elif diff < 0:
                fall -= diff

    return rise, fall
