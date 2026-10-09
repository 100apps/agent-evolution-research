"""Run with python -m unittest discover -s THIS_DIRECTORY -p 'test_*.py'."""
import unittest
import enrich_local_metadata as m
class ExtractorTests(unittest.TestCase):
 def test_exact_ids(self):
  self.assertEqual(m.ids_from_urls(['https://arxiv.org/pdf/2406.07496v2.pdf']),{'arxiv_id':'2406.07496'})
  self.assertEqual(m.ids_from_urls(['https://openreview.net/forum?id=VdVV24KSWK']),{'openreview_id':'VdVV24KSWK'})
  self.assertEqual(m.ids_from_urls(['https://openreview.net/group?id=ICLR.cc/2026/Conference']),{})
  self.assertEqual(m.ids_from_urls(['https://evil.test/abs/2406.07496']),{})
 def test_no_country_from_institution(self):
  for name in ('Tsinghua University','University of California, Berkeley','National University of Singapore','University of Science and Technology of China'):
   self.assertEqual(m.affiliation(name)['country_code'],'')
 def test_explicit_country_only(self):
  self.assertEqual(m.affiliation('Example Laboratory, Beijing, China')['country_code'],'CN')
  self.assertEqual(m.affiliation('Example Laboratory, USA')['country_code'],'US')
  self.assertEqual(m.affiliation('Example Laboratory, USA','publication_time_unverified')['country_code'],'')
 def test_parenthetical_multi_and_order(self):
  a,status,_=m.parse_system_authors({'venue':'SOSP','year':2025,'authors':'A One (Google and University of Utah), B Two (Example (Campus)) and C Three (MIT)'})
  self.assertEqual([x['name'] for x in a],['A One','B Two','C Three'])
  self.assertEqual(a[0]['affiliations'][0]['name'],'Google and University of Utah')
  self.assertEqual(a[1]['affiliations'][0]['name'],'Example (Campus)')
 def test_no_backward_affiliation_inference(self):
  a,_,_=m.parse_system_authors({'venue':'SOSP','year':2026,'authors':'A One, B Two (Example University)'})
  self.assertEqual(a[0]['affiliations'],[])
  self.assertEqual(a[1]['affiliations'][0]['name'],'Example University')
 def test_ambiguous_osdi_retained_not_guessed(self):
  a,status,reason=m.parse_system_authors({'venue':'OSDI','year':2026,'authors':'A One, B Two, University of California, Riverside'})
  self.assertEqual(a,[]);self.assertEqual(status,'unparsed');self.assertTrue(reason)
 def test_colon_pair(self):
  a,_,_=m.parse_system_authors({'venue':'KDD','year':2020,'authors':'A One: Example Labs; B Two: Other University'})
  self.assertEqual([x['name'] for x in a],['A One','B Two'])
  self.assertEqual(a[0]['affiliations'][0]['name'],'Example Labs')
if __name__=='__main__':unittest.main()

class CompactEvidenceTests(unittest.TestCase):
 def test_missing_source_author_slot_preserved(self):
  self.assertEqual(m.author('')['name_status'],'missing_source_name')
 def test_compact_evidence_has_manifest_reference(self):
  ev={'source_path':'conferences/a.json','source_sha256':'abc','source_url':'https://example.org/a','locator':'line:2','method':'exact_id'}
  got=m.compact_provenance({'authors':{'status':'present','missing_reason':'','evidence':[ev]}})['authors']['evidence'][0]
  self.assertEqual(got['source_ref'],m.source_id(ev['source_path'],ev['source_sha256']))
  self.assertNotIn('source_path',got);self.assertNotIn('source_sha256',got)
