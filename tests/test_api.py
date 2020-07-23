
def test_features(api, wiki):
    assert len(api.features) == 9
    assert len(api.features['GB021'].domain) == 2
    f = api.features['GB021']
    assert f.description
    assert f.name
    assert f.patron
    assert f.id
    assert 'Documentation' in api.features['GB020'].description


def test_bib(api):
    assert len(api.bib) == 3


def test_sheets(api):
    assert len(list(api.iter_sheets())) == 2
