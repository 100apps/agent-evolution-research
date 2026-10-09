"""Additional REQUIRED-field/type/provenance gate for decoded master records.
This is not a substitute for semantic review, source verification, or a CSV parser.
Run after decoding each *_json cell with json.loads; do not pass raw CSV strings.
"""
from pathlib import Path
import json,re
from classifier_reference import validate_record,TAXONOMY
ROOT=Path(__file__).resolve().parent
SCHEMA=json.loads((ROOT/'master_csv_schema.json').read_text(encoding='utf-8'))
ENUMS={
 'dedup_status':{'single_source','identifier_matched','title_author_reviewed','unresolved'},
 'abstract_status':{'present','missing','truncated','unverified'},
 'classification_status':set(TAXONOMY['classification_statuses']),
 'classification_label_status':{'candidate','accepted','disputed','unassigned'},
 'classification_basis':{'title_only','title_abstract','title_abstract_fulltext','metadata_only'},
 'review_status':set(TAXONOMY['review_status_values']),
 'author_affiliation_completeness':{'complete','partial','missing','unstructured','not_checked'},
 'affiliation_temporal_status':{'paper_scoped','profile_time_unverified','mixed','paper_reported_unlinked','missing','not_checked'},
 'institution_resolution_status':{'verified_all','verified_partial','unresolved','not_checked','missing'},
 'country_coverage_status':{'complete_known_author_affiliations','partial','missing','not_checked','conflict'}}

def validate_master_schema(row):
    errors=[]
    if not isinstance(row,dict):return ['Master record must be an object']
    for f in SCHEMA['fields']:
        name,typ=f['name'],f['type']
        if name not in row:
            if f['required']:errors.append(f'Missing required field: {name}')
            continue
        x=row[name]
        if typ=='json_array_or_null':good=x is None or isinstance(x,list)
        elif typ=='json_array':good=isinstance(x,list)
        elif typ=='json_object_or_null':good=x is None or isinstance(x,dict)
        elif typ=='json_object':good=isinstance(x,dict)
        elif typ=='integer':good=isinstance(x,int) and not isinstance(x,bool)
        elif typ=='integer_or_empty':good=x=='' or (isinstance(x,int) and not isinstance(x,bool))
        elif typ in ('string','enum','datetime'):good=isinstance(x,str) and (bool(x.strip()) or (typ=='string' and not f['required']))
        elif typ in ('string_or_empty','url_or_empty','datetime_or_empty'):good=isinstance(x,str)
        else:good=False
        if not good:errors.append(f'Wrong type/value for {name}: expected {typ}');continue
        if typ=='enum' and name in ENUMS and x not in ENUMS[name]:errors.append(f'Unknown enum value for {name}')
        if typ=='url_or_empty' and x and not re.match(r'^https?://',x):errors.append(f'Invalid URL: {name}')
    # Avoid crashes from partial/wrongly typed records before deeper validation.
    if errors:return errors
    # Guard nested JSON shapes before calling the narrower classification helper.
    for key in ('category_ids_l1_json','category_ids_l2_json','category_ids_l3_json'):
        if any(not isinstance(x,str) for x in row[key]):errors.append(f'{key} entries must be strings')
    if any(not isinstance(path,list) or any(not isinstance(x,str) for x in path) for path in row['category_paths_json']):
        errors.append('category_paths_json entries must be arrays of ID strings')
    for e in row['category_evidence_json']:
        if not isinstance(e,dict):errors.append('category_evidence_json entries must be objects');continue
        if not isinstance(e.get('category_id'),str) or not isinstance(e.get('source_field'),str):
            errors.append('Evidence category_id and source_field must be strings')
    for author in row['author_affiliations_json'] or []:
        if not isinstance(author,dict):errors.append('author_affiliations_json entries must be objects');continue
        affs=author.get('affiliations',[])
        if not isinstance(affs,list):errors.append('Author affiliations must be an array');continue
        if any(not isinstance(a,dict) for a in affs):errors.append('Nested affiliation entries must be objects')
    if any(not isinstance(x,str) for x in row['countries_json'] or []):errors.append('countries_json entries must be code strings')
    for e in row['country_evidence_json'] or []:
        if not isinstance(e,dict):errors.append('country_evidence_json entries must be objects');continue
        if 'country_code' in e and not isinstance(e['country_code'],str):errors.append('Country evidence country_code must be a string')
    if errors:return errors
    errors.extend(validate_record(row))
    if row['authors_json'] is not None and any(not isinstance(n,str) or not n.strip() for n in row['authors_json']):
        errors.append('authors_json must remain ordered name strings; rich author objects belong in author_affiliations_json')
    if row['abstract_char_count']!=len(row['abstract']):errors.append('abstract_char_count mismatch')
    if row['abstract_status']=='missing' and row['abstract']:errors.append('Missing abstract must have empty text')
    if row['abstract_status']=='present' and not row['abstract']:errors.append('Present abstract cannot be empty')
    if not row['source_urls_json']:errors.append('source_urls_json cannot be empty for a corpus record')
    prov=row['field_provenance_json']
    for field in ('title','abstract','authors','institutions','countries'):
        p=prov.get(field)
        if not isinstance(p,dict) or not p.get('status'):errors.append(f'Field provenance status missing: {field}');continue
        if p['status'] in ('missing','not_checked','unknown'):
            if not p.get('missing_reason'):errors.append(f'Missing-reason required: {field}')
        elif not p.get('source_url') and not p.get('evidence'):errors.append(f'Field provenance source/evidence missing: {field}')
    inputs=row['classification_input_fields_json']
    if not inputs:errors.append('classification_input_fields_json must document actual input/hash even when classifier abstains')
    for item in inputs:
        if not isinstance(item,dict) or not item.get('field') or not re.fullmatch(r'[0-9a-f]{64}',str(item.get('sha256',''))):
            errors.append('Classification input must have field and 64-character lowercase sha256')
    for i,e in enumerate(row['category_evidence_json']):
        for field in SCHEMA['evidence_contract']['required_per_label']:
            if field not in e:errors.append(f'Evidence {i} missing {field}')
        for field in ('basis','rationale_zh','review_status'):
            if not e.get(field):errors.append(f'Evidence {i} empty {field}')
        if e.get('basis')=='lexical_rule_candidate' and not e.get('rule_ids'):errors.append(f'Evidence {i}: lexical rule requires rule_ids')
    for key in ('authors','affiliations','institutions','countries','institution_ids'):
        if key not in row['metadata_field_status_json']:errors.append(f'Metadata field status missing: {key}')
    coverage=row['metadata_field_coverage_json']
    for key in ('author_slots_total','author_slots_structured','author_slots_with_any_affiliation','author_slots_with_publication_affiliation','author_slots_with_explicit_country'):
        if key not in coverage:errors.append(f'Metadata coverage missing: {key}')
        elif coverage[key] is not None and (not isinstance(coverage[key],int) or isinstance(coverage[key],bool) or coverage[key]<0):errors.append(f'Metadata coverage count invalid: {key}')
    for author in row['author_affiliations_json'] or []:
        if not isinstance(author,dict) or not author.get('occurrence_id') or 'author_position' not in author:
            errors.append('Author-affiliation record needs occurrence_id and author_position');continue
        for aff in author.get('affiliations',[]):
            if not aff.get('temporal_status'):errors.append('Affiliation temporal_status missing')
            if aff.get('country_code') and aff.get('temporal_status')=='publication_time_unverified':errors.append('Profile affiliation cannot supply historical country')
            if not aff.get('country_code') and not aff.get('country_missing_reason'):errors.append('Affiliation country missing-reason required')
    country_codes=set(row['countries_json'] or [])
    supported=set()
    for e in row['country_evidence_json'] or []:
        if not isinstance(e,dict):errors.append('Country evidence must be an object');continue
        if e.get('temporal_status') not in ('paper_scoped_explicit','paper_explicit','paper_reported_unlinked'):
            errors.append('Country evidence must be paper-time affiliation scoped')
        if e.get('country_status') not in ('explicit_location_token','separately_verified_paper_location'):
            errors.append('Country lacks supported location status')
        if not e.get('source_url') and not e.get('evidence_refs'):errors.append('Country source/evidence missing')
        if e.get('country_code'):supported.add(e['country_code'])
    if country_codes != supported:errors.append('Flat country codes and country evidence do not agree')
    return errors


def validate_source_coverage_row(row):
    c=SCHEMA['source_coverage_manifest_contract'];errors=[]
    for name in c['required_columns']:
        if name not in row:errors.append(f'Missing source coverage field {name}')
    if errors:return errors
    if row['event_status'] not in c['event_status']:errors.append('Invalid event_status')
    if row['collection_status'] not in c['collection_status']:errors.append('Invalid collection_status')
    if row['event_status']=='no_event' and row['observed_occurrences'] not in (0,'',None):errors.append('no_event conflicts with observed records')
    return errors

if __name__=='__main__':
    cases=[{}, {'classification_status':'insufficient_evidence','taxonomy_version':TAXONOMY['version']}, {'authors_json':'wrong','abstract_status':'wrong'}]
    assert all(validate_master_schema(c) for c in cases)
    print(json.dumps({'schema_version':SCHEMA['schema_version'],'required_field_type_smoke_tests':'passed','production_records_validated':0,'note':'Full corpus must still be passed through this gate after decoding JSON cells. Structural gates do not certify semantic correctness.'},indent=2))
