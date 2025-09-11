import pytest
from core.numbering.heading_numbering import extract_headings_with_numbers


def test_dev_portal_user_skips_toc():
    headings = extract_headings_with_numbers('real-docs/dev-portal-user.docx')
    texts = [h.text for h in headings]
    assert headings[0].text == 'Общие сведения'
    assert headings[0].number == '1'
    assert 'Содержание' not in texts


def test_dev_portal_admin_skips_front_matter():
    headings = extract_headings_with_numbers('real-docs/dev-portal-admin.docx')
    texts = [h.text for h in headings]
    assert headings[0].text == 'Общие сведения'
    assert headings[0].number == '1'
    assert 'АННОТАЦИЯ' not in texts
    assert 'СОДЕРЖАНИЕ' not in texts
