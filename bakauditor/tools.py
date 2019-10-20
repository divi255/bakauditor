def bytes_to_iso(i):
    numbers = [(1000, 'k'), (1000000, 'M'), (1000000000, 'G'),
               (1000000000000, 'T')]
    if i < 1000:
        return '{} B'.format(i)
    for n in numbers:
        if i < n[0] * 1000:
            return '{:.1f} {}B'.format(i / n[0], n[1])
    return '{:.1f} PB'.format(i)


def iso_to_bytes(i):
    numbers = {'K': 1000, 'M': 1000000, 'G': 1000000000, 'T': 1000000000000}
    try:
        return int(i)
    except:
        pass
    try:
        n = numbers[i[-1].upper()]
    except:
        raise ValueError('Invalid size: {}'.format(i))
    return float(i[:-1]) * n
