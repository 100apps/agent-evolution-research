import json,copy,datetime,email.utils,pathlib
import jsonschema
P=pathlib.Path(__file__).parent
s=json.loads((P/'metrics_schema.json').read_text());jsonschema.Draft202012Validator.check_schema(s)
v=jsonschema.Draft202012Validator(s,format_checker=jsonschema.FormatChecker())
b=json.loads((P/'semantic_scholar_probe.json').read_text());m=json.loads((P/'semantic_scholar_probe_manifest.json').read_text())
t=email.utils.parsedate_to_datetime(m['headers']['Date']).isoformat();asof=t[:10]
src={'provider':'semantic_scholar','record_id':b['paperId'],'source_url':m['url'],'retrieved_at':t,'provider_updated_at':None,'raw_sha256':m['sha256'],'raw_field':'citationCount','request_fingerprint':None,'identifier_match':'exact_arxiv','matched_identifier':'1706.03762'}
metric={'metric':'citation_count','value':b['citationCount'],'status':'present','missing_reason':None,'as_of':t,'unit':'citing_papers','window':{'kind':'lifetime_to_asof','start':None,'end':asof,'definition':'Provider graph count observed in HTTP response; source internal counting cutoff unavailable.'},'source':src,'method_version':None,'caveats':['One-record field probe, not a master CSV join or coverage estimate. HTTP Date used as response observation timestamp.']}
age={'days':(datetime.date.fromisoformat(asof)-datetime.date.fromisoformat(b['publicationDate'])).days,'as_of':asof,'date_used':b['publicationDate'],'date_precision':'day','basis':'provider_publication_date','status':'present','missing_reason':None,'source':dict(src,raw_field='publicationDate')}
r={'schema_version':'paper-impact-v1.0.0-proposed','paper_id':'example:arxiv:1706.03762','publication_age':age,'citation_observations':[metric],'citation_counts_by_year':[],'normalized_citation_observations':[],'usage_observations':[],'public_reviews':[],'artifact_links':[],'integrity_events':[],'collection_status':{'openalex':{'status':'not_requested','missing_reason':'Research worker did not call OpenAlex API.','attempted_at':None},'arxiv_usage':{'status':'not_exposed','missing_reason':'Standard article metadata API exposes no per-article usage metric.','attempted_at':None}},'adapter_version':'contract-example-v1'}
v.validate(r)
(P/'example_semantic_scholar_observation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
passed=['schema_valid','actual_single_record_fixture_valid']
for name,modify in [
 ('reject_missing_as_zero',lambda x:x['citation_observations'][0].update(status='rate_limited',value=0,missing_reason='429')),
 ('reject_negative_citation',lambda x:x['citation_observations'][0].update(value=-1)),
 ('reject_fractional_citation',lambda x:x['citation_observations'][0].update(value=0.4)),
 ('reject_year_only_day_age',lambda x:x['publication_age'].update(date_precision='year')),
 ('reject_quality_score_column',lambda x:x.update(quality_score=0.3))]:
 x=copy.deepcopy(r);modify(x)
 assert list(v.iter_errors(x)),name
 passed.append(name)
x=copy.deepcopy(r);x['citation_observations'][0]['value']=0;v.validate(x);passed.append('accept_explicit_zero')
x=copy.deepcopy(r);x['citation_observations'][0].update(status='rate_limited',value=None,missing_reason='429');v.validate(x);passed.append('accept_null_on_429')
assert len(s['x_csv_required_first_release'])==6
(P/'validation.json').write_text(json.dumps({'passed':passed,'first_release_columns':s['x_csv_required_first_release'],'optional_columns':s['x_csv_optional_only_if_observed'],'scope':'Contract/schema fixtures only; no master CSV processed, no collector executed.'},indent=2)+'\n')
print(json.dumps({'tests_passed':len(passed),'required_csv_columns':6,'optional_if_real':2}))
