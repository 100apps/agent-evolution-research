"""Small deterministic lexical regression tests, not a semantic accuracy audit."""
import unittest
import compare_titles as m
class RulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiled={k:[m.re.compile(r'\b(?:'+p+r')\b') for p in r.get('patterns',[])] for k,r in m.RULES.items()}
    def tags(self,s):return m.classify(m.norm(s),m.RULES,self.compiled)
    def test_agents_conjunction(self):
        self.assertIn('agents_broad',self.tags('Multi-Agent Reinforcement Learning'))
        self.assertNotIn('agents_language_action_strict',self.tags('Multi-Agent Reinforcement Learning'))
        self.assertIn('agents_language_action_strict',self.tags('Tool Calling with Large Language Models'))
        self.assertNotIn('agents_broad',self.tags('Memory Efficient Language Models'))
    def test_posttraining_context(self):
        self.assertIn('posttraining_named_broad',self.tags('DPO Improves Preferences'))
        self.assertNotIn('posttraining_model_context',self.tags('DPO Improves Preferences'))
        self.assertIn('posttraining_model_context',self.tags('RLVR for Large Language Models'))
        self.assertNotIn('posttraining_model_context',self.tags('Fine-tuning Language Models'))
    def test_pretraining_distinction(self):
        self.assertIn('pretraining_explicit',self.tags('Pre-Training a Model'))
        self.assertNotIn('pretraining_explicit',self.tags('Using Pre-trained Models'))
        self.assertIn('pretrained_usage_cue',self.tags('Using Pre-trained Models'))
    def test_old_new_terms(self):
        self.assertNotIn('modern_foundation_llm',self.tags('BERT is a Language Model'))
        self.assertIn('historical_pretrained',self.tags('BERT is a Language Model'))
        self.assertNotIn('modern_foundation_llm',self.tags('GPT-GNN for Graph Learning'))
        self.assertIn('modern_foundation_llm',self.tags('GPT-4 Reasoning'))
        self.assertIn('language_model_context',self.tags('Language Models are Few-Shot Learners'))
        self.assertNotIn('modern_foundation_llm',self.tags('Language Models are Few-Shot Learners'))
    def test_ambiguous_terms_excluded(self):
        self.assertNotIn('inference_serving_gpu',self.tags('Statistical Inference with Bayesian Priors'))
        self.assertNotIn('safety_security',self.tags('Inductive Bias and Geometric Alignment'))
        self.assertNotIn('systems_storage_networking',self.tags('Deep Neural Networks'))
        self.assertIn('systems_storage_networking',self.tags('A High-Performance Network Stack'))
    def test_matched_spans(self):
        s=m.norm('LLM Agents: TOOL-Calling')
        for evidence in self.tags(s).values():
            for span in evidence['spans']:self.assertEqual(s[span['start']:span['end']],span['text'])
if __name__=='__main__':unittest.main()
