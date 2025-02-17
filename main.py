from pathlib import Path

import docutils
import docutils.nodes
import docutils.parsers.rst
import docutils.utils
import genanki
import requests

CSS = """.card {
 font-family: Monospace, sans-serif;
 font-size: 1.2rem;
 max-width: 960px;
 margin: 0 auto;
}
.cloze {
 font-weight: medium;
 font-style: italic;
 color: #9ccc65;
}
"""

anki_model = genanki.Model(
    1607392319,
    'Basic Model',
    fields=[
        {'name': 'Question'},
        {'name': 'Answer'},
        {'name': 'Image'},
    ],
    templates=[
        {
            'name': 'Basic Card',
            'qfmt': '{{Question}}',
            'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}<hr id="media">{{Image}}',
        },
    ],
    css=CSS,
)

anki_model_cloze = genanki.Model(
    998877661,
    'Cloze Model',
    fields=[
        {'name': 'Question'},
        {'name': 'Answer'},
        {'name': 'Image'},
    ],
    templates=[
        {
            'name': 'Cloze Card',
            'qfmt': '{{cloze:Question}}',
            'afmt': '{{cloze:Question}}<hr id="answer">{{Answer}}<hr id="media">{{Image}}',
        },
    ],
    css=CSS,
    model_type=genanki.Model.CLOZE)

headers = {
    'headers': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}


def walk(path):
    # traverse all files from current directory
    for p in Path(path).iterdir():
        if p.is_dir():
            continue
        yield p.resolve()


def parse_rst(input_file: str) -> docutils.nodes.document:
    text = Path(input_file).read_text()
    parser = docutils.parsers.rst.Parser()
    components = (docutils.parsers.rst.Parser,)
    settings = docutils.frontend.OptionParser(
        components=components
    ).get_default_values()
    document = docutils.utils.new_document("<rst-doc>", settings=settings)
    parser.parse(text, document)
    return document


def generate_apkg(file_name):
    my_deck = genanki.Deck(
        2059400110,
        file_name.title())

    # DUMMY parsing (probably exist better method just to parse this into html)
    document = parse_rst(f'{file_name}.rst')
    media_files = []
    for i, note in enumerate(document):
        section = {
            'name': f'Card {i}',
            'type': 'basic',
            'tags': [],
            'media_files': [],
            'media_tags': [],
            'question': [],
            'answer': []
        }

        active_section = 'question'

        for children in note.children:
            if children.tagname == 'title':
                section['tags'] = children.astext().replace(' ', '').split(',')
            elif children.tagname == 'comment':
                if children.children[0] == 'answer':
                    active_section = 'answer'
            elif children.tagname == 'image':
                section['media_files'].append(children.attributes['uri'])
                section['media_tags'].append(
                    f'<img src="{children.attributes["uri"].replace("img/", "")}" alt="{children.attributes["alt"]}">'
                )
            elif children.tagname in ('bullet_list', 'enumerated_list'):
                list_tag = 'ol' if children.tagname == 'enumerated_list' else 'ul'
                list_items = [
                    f'<li>{list_item.astext()}</li>'
                    for list_item in children.children
                ]
                section[active_section].append(
                    f'<{list_tag}>{"".join(list_items)}</{list_tag}>'
                )

            elif children.tagname == 'paragraph':
                section = parse_paragraph(active_section, children, section)

        model = anki_model

        if section['type'] == 'cloze':
            model = anki_model_cloze

        my_note = genanki.Note(
            model=model,
            fields=[
                '\n\n'.join(section['question']),
                '\n\n'.join(section['answer']),
                '<br>'.join(section['media_tags']),
            ])

        my_deck.add_note(my_note)
        media_files += section['media_files']

    my_package = genanki.Package(my_deck)
    my_package.media_files = list(set(media_files))
    my_package.write_to_file(f'{file_name}.apkg')


def parse_paragraph(active_section, children, section):
    element_text = children.astext()
    if '{{' in element_text:
        section['type'] = 'cloze'
    # Generate urls if needed
    if element_text.startswith('http'):
        url_document = requests.get(element_text, headers=headers)
        url_document_text = url_document.text
        url_document_title = url_document_text[
                             url_document_text.find('<title>') + 7:
                             url_document_text.find('</title>')]

        section[active_section].append(f'<p><a href="{element_text}">'
                                       f'{url_document_title or element_text}'
                                       f'</a></p>')
    else:
        section[active_section].append(f'<p>{element_text}</p>')

    return section


def generate_apkgs():
    # Generate packages from *.rst files
    for p in walk(Path('.')):
        if p.suffix == '.rst' and p.stem != 'README':
            generate_apkg(p.stem)


if __name__ == '__main__':
    generate_apkgs()
