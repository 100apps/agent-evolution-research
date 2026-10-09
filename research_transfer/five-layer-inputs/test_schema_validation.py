import copy,hashlib,unittest
from schema_validation import SCHEMA,TAXONOMY,validate_master_schema

def synthetic_record():
    r={}
    for f in SCHEMA['fields']:
        typ=f['type'];r[f['name']]=[] if typ=='json_array' else {} if typ=='json_object' else None if typ in ('json_array_or_null','json_object_or_null') else 0 if typ=='integer' else ''
    r.update(paper_id='synthetic:test',title='Ambiguous title',publication_year='',year_basis='not_known',dedup_status='unresolved',abstract_status='missing',classification_status='insufficient_evidence',classification_label_status='unassigned',classification_method='synthetic_fixture',classifier_version='test-only',taxonomy_version=TAXONOMY['version'],classification_basis='title_only',classification_reason='Synthetic schema fixture with insufficient evidence.',review_status='automated',record_updated_at='2026-10-09T00:00:00Z',author_affiliation_completeness='not_checked',affiliation_temporal_status='not_checked',institution_resolution_status='not_checked',country_coverage_status='not_checked')
    r['source_urls_json']=['https://example.invalid/synthetic-fixture']
    r['classification_input_fields_json']=[{'field':'title','sha256':hashlib.sha256(r['title'].encode()).hexdigest()}]
    r['field_provenance_json']={'title':{'status':'synthetic_fixture','source_url':r['source_urls_json'][0]},**{key:{'status':'missing','missing_reason':'synthetic_fixture_not_provided'} for key in ('abstract','authors','institutions','countries')}}
    r['metadata_field_status_json']={key:'not_checked' for key in ('authors','affiliations','institutions','countries','institution_ids')}
    r['metadata_missing_reasons_json']={key:'synthetic_fixture_not_provided' for key in r['metadata_field_status_json']}
    r['metadata_field_coverage_json']={key:None for key in ('author_slots_total','author_slots_structured','author_slots_with_any_affiliation','author_slots_with_publication_affiliation','author_slots_with_explicit_country')}
    return r

class SchemaValidationTests(unittest.TestCase):
    def test_full_synthetic_record_passes(self):self.assertEqual(validate_master_schema(synthetic_record()),[])
    def test_two_field_record_fails(self):self.assertTrue(validate_master_schema({'classification_status':'insufficient_evidence','taxonomy_version':TAXONOMY['version']}))
    def test_wrong_authors_type_fails(self):
        r=synthetic_record();r['authors_json']='wrong';self.assertTrue(validate_master_schema(r))
    def test_invalid_abstract_status_fails(self):
        r=synthetic_record();r['abstract_status']='wrong';self.assertTrue(validate_master_schema(r))
    def test_empty_field_provenance_fails(self):
        r=synthetic_record();r['field_provenance_json']={};self.assertTrue(validate_master_schema(r))
    def test_empty_input_hashes_fail(self):
        r=synthetic_record();r['classification_input_fields_json']=[];self.assertTrue(validate_master_schema(r))
    def test_unsupported_country_fails(self):
        r=synthetic_record();r['countries_json']=['CN'];self.assertTrue(validate_master_schema(r))
    def test_null_evidence_returns_error(self):
        r=synthetic_record();r['category_evidence_json']=[None];self.assertTrue(validate_master_schema(r))
    def test_null_nested_affiliation_returns_error(self):
        r=synthetic_record();r['author_affiliations_json']=[{'occurrence_id':'test','author_position':1,'affiliations':[None]}];self.assertTrue(validate_master_schema(r))
    def test_profile_country_fails(self):
        r=synthetic_record();r['author_affiliations_json']=[{'occurrence_id':'synthetic:1','author_position':1,'affiliations':[{'name':'Test','temporal_status':'publication_time_unverified','country_code':'CN'}]}];self.assertTrue(validate_master_schema(r))
if __name__=='__main__':unittest.main()
