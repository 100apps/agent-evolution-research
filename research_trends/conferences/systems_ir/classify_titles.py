"""Title-only vocabulary proxies. Labels overlap; complements mean no marker detected, NOT non-AI."""
from pathlib import Path
import json,re,csv,collections,hashlib
P=Path(__file__).parent
# No generic 'model', 'training', 'inference', 'agent', 'intelligent', or 'generation' in broad AI.
LEXICON={
 'language_model_explicit':r'large[- ]language[- ]models?|\b(?:m?llms?|chatgpt|gpt[- ]?[2345](?:\.\d)?|bert|roberta|t5)\b|foundation[- ]models?|generative[- ]ai|language[- ]models?',
 'llm_generative_explicit':r'large[- ]language[- ]models?|\b(?:m?llms?|chatgpt|gpt[- ]?[2345](?:\.\d)?)\b|foundation[- ]models?|generative[- ]ai|retrieval[- ]augmented[- ]generation|\brag\b',
 'learning_extended':r'\blearning\b|\blearned\b|\bembeddings?\b',
 'ai_ml_explicit':r'distributed[- ]training|(?:large[- ])?model[- ](?:training|inference|serving)|\bai\b|artificial[- ]intelligence|machine[- ]learning|deep[- ]learning|\bneural\b|\b(?:dnn|cnn|rnn|lstm|gnn|gcn|gan)s?\b|\btransformers?\b|reinforcement[- ]learning|federated[- ]learning|contrastive[- ]learning|representation[- ]learning|meta[- ]learning|multi[- ]task[- ]learning|self[- ]supervised|semi[- ]supervised|unsupervised[- ]learning|supervised[- ]learning|transfer[- ]learning|\blearned\b|graph[- ]convolution|convolutional|autoencod\w*|diffusion[- ]models?|generative[- ]models?|pre[- ]?train\w*|fine[- ]tun\w*|prompt\w*|zero[- ]shot|few[- ]shot|in[- ]context[- ]learning|knowledge[- ]distill\w*|\brl[- ]agent',
 'retrieval_recommendation_ranking':r'retriev\w*|recommend\w*|\brank\w*|\bre[- ]?rank\w*|search[- ]engines?|information[- ]access|collaborative[- ]filter\w*|\bsearch\b',
 'data_mining_core':r'\bmining\b|clustering|classification|regression|anomaly|outlier|causal|time[- ]series|forecast\w*|pattern\w*|graph\w*|tabular|data[- ](?:cleaning|integration|preprocessing)|\bstream\w*|\boptimiza\w*',
 'software_testing_analysis':r'\btest\w*|fuzz\w*|\bbugs?\b|defect\w*|debug\w*|verif\w*|static[- ]analysis|dynamic[- ]analysis|program[- ]analysis|vulnerab\w*|program[- ]repair',
 'software_code_generation':r'code[- ](?:generation|generating|synthesis|completion)|generating[- ]code|program[- ]synthesis|program[- ]repair|code[- ]repair|automated[- ]repair|code[- ]translation|code[- ]summari\w*|code[- ]review',
 'systems_ai_infrastructure':r'distributed[- ]training|(?:large[- ])?model[- ](?:training|inference|serving)|\bgpus?\b|\btensor\w*|(?:model|neural|deep[- ]learning|llm)[- ](?:training|inference|serving)|(?:training|inference|serving).{0,45}(?:language[- ]model|llm|neural|deep[- ]learning)|(?:language[- ]model|llm).{0,45}(?:training|inference|serving)|\bai[- ](?:workloads?|systems?|clusters?)',
 'agents_explicit':r'\bagents?\b|agentic|multi[- ]agent',
}
compiled={k:re.compile(v,re.I) for k,v in LEXICON.items()}
rows=[json.loads(x) for x in (P/('combined_papers.jsonl' if (P/'combined_papers.jsonl').exists() else 'papers.jsonl')).read_text().splitlines()]
sysfile=P/'systems'/'papers.jsonl'
if sysfile.exists():
 # systems worker schema checked separately before merging final combined.
 pass
for r in rows:
 matches={k:sorted(set(m.group(0).lower() for m in pat.finditer(r['title']))) for k,pat in compiled.items()}
 matches['ai_any']=sorted(set(matches['language_model_explicit']+matches['llm_generative_explicit']+matches['ai_ml_explicit']))
 matches['ai_learning_extended']=sorted(set(matches['ai_any']+matches['learning_extended']));r['title_marker_matches']=matches;r['title_flags']={k:bool(v) for k,v in matches.items()}
with open(P/'papers_labeled.jsonl','w',encoding='utf8') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
agg=[]
for (v,y),rs in sorted(__import__('itertools').groupby([],lambda x:x)) if False else []:pass
for v,y in sorted({(r['venue'],r['year']) for r in rows}):
 rs=[r for r in rows if (r['venue'],r['year'])==(v,y)];n=len(rs)
 a={'venue':v,'year':y,'traditional_domain_main_papers':n,'ai_marker_n':sum(r['title_flags']['ai_any'] for r in rs),'llm_marker_n':sum(r['title_flags']['llm_generative_explicit'] for r in rs)}
 a['ai_learning_extended_n']=sum(r['title_flags']['ai_learning_extended'] for r in rs)
 a['no_ai_marker_n']=n-a['ai_marker_n'];a['ai_marker_share']=a['ai_marker_n']/n;a['llm_marker_share']=a['llm_marker_n']/n
 for k in LEXICON:
  a[k+'_n']=sum(r['title_flags'][k] for r in rs)
  a[k+'_and_ai_n']=sum(r['title_flags'][k] and r['title_flags']['ai_any'] for r in rs)
 agg.append(a)
(P/'title_topic_counts.json').write_text(json.dumps(agg,ensure_ascii=False,indent=2))
with open(P/'title_topic_counts.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=agg[0]);w.writeheader();w.writerows(agg)
(P/'title_lexicon.json').write_text(json.dumps({'version':'systems_ir_title_v1','basis':'title_only','lexicon':LEXICON,'ai_any':'union(language_model_explicit, llm_generative_explicit, ai_ml_explicit)','warning':'Dictionary proxy, not paper-topic ground truth. Whole venue belongs the traditional domain. AI and traditional labels overlap. No marker is not proof of non-AI. Plain agent not in AI union. BERT counts as language model, but not generative LLM. learning_extended is a deliberately broader sensitivity proxy and can include human-learning false positives.'},indent=2))
print('venue year all AI-marker LLM-marker no-AI-marker')
for a in agg:print(a['venue'],a['year'],a['traditional_domain_main_papers'],a['ai_marker_n'],a['llm_marker_n'],a['no_ai_marker_n'])
