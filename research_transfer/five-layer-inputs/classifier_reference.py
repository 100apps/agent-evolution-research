"""Dependency-free integration helpers; no semantic classifier is implemented here.
The taxonomy is semantic and independent of any downstream keyword baseline.
"""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TAXONOMY = json.loads((ROOT / 'taxonomy.json').read_text(encoding='utf-8'))
NODES = {n['id']: n for n in TAXONOMY['nodes']}


def category_fields(leaf_ids):
    """Deduplicate evidence-supported leaves, then calculate ancestors only."""
    leaf_ids = sorted(set(leaf_ids), key=lambda i: (TAXONOMY['l1_order'].index(i[0]), i))
    for leaf in leaf_ids:
        if leaf not in NODES or NODES[leaf]['level'] != 3:
            raise ValueError(f'Unknown or non-L3 category: {leaf}')
    paths = [NODES[i]['path_ids'] for i in leaf_ids]
    closure = set(x for path in paths for x in path)
    return {
        'category_ids_l1_json': [i for i in TAXONOMY['l1_order'] if i in closure],
        'category_ids_l2_json': sorted(i for i in closure if NODES[i]['level'] == 2),
        'category_ids_l3_json': leaf_ids,
        'category_paths_json': paths,
    }


def make_evidence(category_id, source_field, stored_text, literal_quote, source_url,
                  rationale_zh, *, rule_ids=None, start=None,
                  basis='lexical_rule_candidate', review_status='automated',
                  evidence_strength='needs_review', assignment_role='central_contribution'):
    """Build an auditable span. A literal match is NOT proof of semantic centrality."""
    if category_id not in NODES or NODES[category_id]['level'] != 3:
        raise ValueError('Evidence requires an L3 category.')
    if not literal_quote:
        raise ValueError('Evidence quote must not be empty.')
    start = stored_text.find(literal_quote) if start is None else start
    end = start + len(literal_quote)
    if start < 0 or stored_text[start:end] != literal_quote:
        raise ValueError('Evidence quote is not an exact stored-text span.')
    return {'category_id':category_id,'assignment_role':assignment_role,
            'source_field':source_field,'source_url':source_url,
            'span_start':start,'span_end':end,'quote':literal_quote,
            'rationale_zh':rationale_zh,'evidence_strength':evidence_strength,
            'basis':basis,'rule_ids':rule_ids or [],'review_status':review_status}


def validate_record(record):
    """Validate structural/evidence consistency, not whether labels are semantically right."""
    errors=[]
    def error(msg):errors.append(msg)
    ids=record.get('category_ids_l3_json',[])
    status=record.get('classification_status')
    if status not in TAXONOMY['classification_statuses']:error('Unknown classification_status')
    if status == 'classified' and not ids:error('classified requires at least one L3')
    if status != 'classified' and ids:error('Unclassified/outside/gap status must have no final L3')
    try:
        expected=category_fields(ids)
        for key, value in expected.items():
            actual=record.get(key,[])
            # Leaf/path list ordering is presentation; membership must be identical.
            normal=lambda vals:sorted(json.dumps(v,sort_keys=True) for v in vals)
            if normal(actual)!=normal(value):error(f'Invalid parent closure or paths: {key}')
    except (ValueError, KeyError) as ex:error(str(ex))
    if record.get('taxonomy_version') != TAXONOMY['version']:error('Taxonomy version mismatch')
    evidence=record.get('category_evidence_json',[])
    if set(ids) != set(e.get('category_id') for e in evidence):error('Every label needs evidence, and evidence needs a label')
    for idx,e in enumerate(evidence):
        text=record.get(e.get('source_field'))
        start,end=e.get('span_start'),e.get('span_end')
        if not isinstance(text,str) or not isinstance(start,int) or not isinstance(end,int):
            error(f'Evidence {idx}: source text or offsets missing');continue
        if start<0 or end<=start or end>len(text) or text[start:end]!=e.get('quote'):
            error(f'Evidence {idx}: quote/span mismatch')
        if e.get('evidence_strength') not in TAXONOMY['evidence_strength_values']:error(f'Evidence {idx}: unknown evidence strength')
        if e.get('assignment_role') not in ('central_contribution','primary_object_of_study'):error(f'Evidence {idx}: non-central label role')
        if not e.get('source_url'):error(f'Evidence {idx}: source URL missing')
    if record.get('review_status') == 'automated' and record.get('classification_label_status') not in ('candidate','unassigned'):
        error('Automatic first-pass output must remain candidate or unassigned')
    if 'confidence' in record or 'confidence_probability' in record:
        error('Do not add an unvalidated probability field to this schema')
    if record.get('classification_basis') == 'title_abstract' and not record.get('abstract'):
        error('Missing abstract contradicts claimed title_abstract basis')
    return errors


def validate_boundary_prediction(test, prediction):
    """Use this adapter to test a REAL classifier's output on each supplied fixture."""
    errors=[];expected=test['expected'];ids=set(prediction.get('category_ids_l3_json',[]))
    all_ids={x for i in ids if i in NODES for x in NODES[i]['path_ids']}
    if prediction.get('classification_status') != expected['classification_status']:
        errors.append('Wrong classification_status')
    for i in expected['required_l3_ids']:
        if i not in ids:errors.append(f'Missing required {i}')
    for prefix in expected['forbidden_ids_or_prefixes']:
        if any(i==prefix or i.startswith(prefix+'.') for i in all_ids):errors.append(f'Forbidden assignment {prefix}')
    facets=prediction.get('facets_json') or {}
    for facet,values in expected.get('facets',{}).items():
        if not set(values).issubset(facets.get(facet,[])):errors.append(f'Missing expected facet {facet}={values}')
    return errors


def write_master_csv(path, records, columns):
    """RFC4180-style CSV with compact JSON values and empty unknown scalars."""
    with open(path,'w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=columns,extrasaction='raise')
        writer.writeheader()
        for record in records:
            row={}
            for column in columns:
                value=record.get(column)
                if column.endswith('_json'):
                    row[column]=json.dumps(value,ensure_ascii=False,separators=(',',':'))
                else:row[column]='' if value is None else value
            writer.writerow(row)


def run_self_tests():
    examples=json.loads((ROOT/'adjudicated_examples.json').read_text(encoding='utf-8'))['examples']
    fixtures=json.loads((ROOT/'adversarial_tests.json').read_text(encoding='utf-8'))['tests']
    assert len(NODES)==len(TAXONOMY['nodes']), 'Duplicate IDs'
    assert len([n for n in NODES.values() if n['level']==1])==5
    leaves=[n for n in NODES.values() if n['level']==3]
    assert 40<=len(leaves)<=70
    for n in NODES.values():
        assert len(n['path_ids'])==n['level']
        if n['parent_id']:assert n['path_ids'][-2]==n['parent_id']
        assert n['children_ids']==[x['id'] for x in NODES.values() if x['parent_id']==n['id']]
    errors={e['example_id']:validate_record(e) for e in examples if validate_record(e)}
    assert not errors,errors
    # Fixture schema/reference IDs only: no semantic classifier has been tested.
    for f in fixtures:
        assert all(i in NODES and NODES[i]['level']==3 for i in f['expected']['required_l3_ids'])
        assert all(i in NODES for i in f['expected']['forbidden_ids_or_prefixes'])
    single=category_fields(['A.01.02'])
    assert single['category_ids_l1_json']==['A'], 'Application dependency must not inherit lower layers'
    both=category_fields(['E.02.02','I.02.04','I.02.04'])
    assert both['category_ids_l1_json']==['E','I'] and len(both['category_ids_l3_json'])==2
    unicode_text='🧠 Agent memory'
    assert make_evidence('A.01.02','title',unicode_text,'Agent memory','https://example.invalid/test','测试')['span_start']==2
    report={
        'taxonomy_version':TAXONOMY['version'],
        'taxonomy_sha256':hashlib.sha256((ROOT/'taxonomy.json').read_bytes()).hexdigest(),
        'node_count':len(NODES),'l1_count':5,'l2_count':sum(n['level']==2 for n in NODES.values()),'l3_count':len(leaves),
        'structural_and_span_validation':'passed','validated_examples':len(examples),
        'boundary_fixture_schema_validation':'passed','boundary_fixture_count':len(fixtures),
        'semantic_classifier_test_status':'not_run_no_corpus_classifier_in_this_package',
        'human_validation_status':'not_run','calibrated_probabilities':'none',
        'scope':'These checks establish schema integrity, evidence-span integrity, and reference invariants. They do not establish classification accuracy.'}
    (ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':print(json.dumps(run_self_tests(),ensure_ascii=False,indent=2))
