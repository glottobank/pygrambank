from clldutils.path import Path
from pycldf import StructureDataset

from pygrambank import cldf


def test_create(api, wiki, capsys):
    cldf.create(api.repos, Path(__file__).parent / 'glottolog', wiki)
    captured = capsys.readouterr()
    assert 'inconsistent' in captured.out
    ds = StructureDataset.from_metadata(api.repos / 'cldf' / 'StructureDataset-metadata.json')
    assert len(list(api.sheets_dir.glob('*.tsv'))) == 4
    assert len(list(ds['LanguageTable'])) == 1