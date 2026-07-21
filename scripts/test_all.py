import sys
import os
import time
import asyncio
import httpx
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.tools.policy_search import get_chroma_collection

MRR_EVAL_DATASET = [('How many days of annual leave do I get?', 'policy_01_annual_leave.pdf'), ('Can I carry over unused vacation days?', 'policy_01_annual_leave.pdf'), ('What are the core working hours for remote workers?', 'policy_02_remote_work.pdf'), ('Do I need manager approval to work from a different country?', 'policy_02_remote_work.pdf'), ('How often are performance reviews conducted?', 'policy_03_performance_review.pdf'), ('What metrics are used in my performance review?', 'policy_03_performance_review.pdf'), ('What is the policy on conflict of interest?', 'policy_04_code_of_conduct.pdf'), ('Can I accept gifts from vendors?', 'policy_04_code_of_conduct.pdf'), ('Is there a budget for professional certifications?', 'policy_05_training_development.pdf'), ('How do I request a reimbursement for a course?', 'policy_05_training_development.pdf')]
COMPREHENSIVE_QUESTIONS = [{'q': 'How many leave days do I have left?', 'source': 'structured_data', 'keywords': ['18', 'eighteen']}, {'q': 'What department do I work in?', 'source': 'structured_data', 'keywords': ['Data', 'AI']}, {'q': 'When was I hired?', 'source': 'structured_data', 'keywords': ['2019']}, {'q': 'What is my remote work model?', 'source': 'structured_data', 'keywords': ['Hybrid Flexible', 'Hybrid', 'Flexible']}, {'q': 'What was my performance rating in 2024?', 'source': 'structured_data', 'keywords': ['4', 'four']}, {'q': 'What is my annual training budget?', 'source': 'structured_data', 'keywords': ['12000', '12,000']}, {'q': 'Which employees in the Data & AI department are on a Hybrid Flexible model?', 'source': 'structured_data', 'keywords': ['Sara']}, {'q': 'How many employees report to Khalid Mansour?', 'source': 'structured_data', 'keywords': ['4', 'four']}, {'q': 'Who in the company has the highest leave balance?', 'source': 'structured_data', 'keywords': ['Sara']}, {'q': 'List all employees rated 4 or above in 2024.', 'source': 'structured_data', 'keywords': ['Sara']}, {'q': 'How many annual leave days does a Junior employee get in their first 2 years?', 'source': 'rag', 'keywords': ['21', 'twenty-one']}, {'q': 'After how many years of service does a Mid-level employee move up to 25 days?', 'source': 'rag', 'keywords': ['3', 'three']}, {'q': 'Does the policy apply to contractors and freelancers?', 'source': 'rag', 'keywords': ['no', 'not apply', 'exclude']}, {'q': 'Can I carry over unused leave to next year, and if so, how many days?', 'source': 'rag', 'keywords': ['yes', '5', 'five']}, {'q': 'After how many months of service am I eligible for remote work?', 'source': 'rag', 'keywords': ['6', 'six']}, {'q': 'What is the difference between Hybrid Standard and Hybrid Flexible?', 'source': 'rag', 'keywords': ['2 days', '20%']}, {'q': 'Can I work fully remotely from another country?', 'source': 'rag', 'keywords': ['no', 'prohibited', 'not allowed']}, {'q': 'How often do performance check-ins happen?', 'source': 'rag', 'keywords': ['quarterly', 'four times', 'four']}, {'q': 'What is the performance rating scale used?', 'source': 'rag', 'keywords': ['1', '5', 'scale']}, {'q': 'Can I dispute my performance rating?', 'source': 'rag', 'keywords': ['yes', 'appeal']}, {'q': 'What is a Performance Improvement Plan (PIP)?', 'source': 'rag', 'keywords': ['PIP']}, {'q': "What is the company's policy on workplace harassment?", 'source': 'rag', 'keywords': ['zero tolerance', 'harassment']}, {'q': 'What counts as a conflict of interest under this policy?', 'source': 'rag', 'keywords': ['financial', 'competitor']}, {'q': 'Can I speak to the media on behalf of the company without approval?', 'source': 'rag', 'keywords': ['no', 'approval']}, {'q': 'What is the annual training budget for a Junior (L1–L2) employee?', 'source': 'rag', 'keywords': ['5000', '5,000']}, {'q': 'Does the training budget roll over to the next year if unused?', 'source': 'rag', 'keywords': ['no', 'does not roll over', 'forfeited']}, {'q': 'Are conference travel costs (flights, hotels) covered by the training budget?', 'source': 'rag', 'keywords': ['no', 'not covered', 'exclude']}, {'q': 'Can I take next Friday off?', 'source': None, 'keywords': ['manager', 'approval', '5 working days']}, {'q': 'What is the weather today in Riyadh?', 'source': 'unknown', 'keywords': ["don't know", 'cannot', 'do not have', 'unable']}, {'q': 'How do I reset my VPN password?', 'source': 'unknown', 'keywords': ["don't know", 'cannot', 'IT', 'unable']}, {'q': "Compare my training budget to my manager's", 'source': None, 'keywords': ["don't know", 'cannot', 'access', 'unable']}, {'q': 'Am I allowed to work remotely from outside Saudi Arabia if I have 4 years of service?', 'source': 'rag', 'keywords': ['no', 'not allowed', 'prohibited']}]

def evaluate_mrr(k: int=5) -> str:
    print('Running MRR Evaluation...')
    collection = get_chroma_collection()
    total_rr = 0.0
    total_time = 0.0
    md_output = ['## Part 1: RAG Retrieval Evaluation (MRR@5)', '', '| Question | Expected Source | Rank Found | Reciprocal Rank | Time (ms) |', '|----------|-----------------|------------|-----------------|-----------|']
    for query, expected_source in MRR_EVAL_DATASET:
        start_time = time.time()
        results = collection.query(query_texts=[query], n_results=k)
        query_time = time.time() - start_time
        total_time += query_time
        metadatas = results.get('metadatas', [[]])[0]
        rank = 0
        rr = 0.0
        for i, meta in enumerate(metadatas):
            if meta and meta.get('source_file') == expected_source:
                rank = i + 1
                rr = 1.0 / rank
                break
        total_rr += rr
        if rank > 0:
            md_output.append(f'| {query} | `{expected_source}` | {rank} | {rr:.2f} | {query_time * 1000:.2f} |')
        else:
            md_output.append(f'| {query} | `{expected_source}` | Not Found | 0.00 | {query_time * 1000:.2f} |')
    mrr = total_rr / len(MRR_EVAL_DATASET)
    avg_time = total_time / len(MRR_EVAL_DATASET) * 1000
    md_output.extend(['', f'**Overall MRR@{k}:** {mrr:.4f}  ', f'**Average Query Time:** {avg_time:.2f}ms', '', '---', ''])
    return '\n'.join(md_output)

async def run_comprehensive_test(mrr_markdown: str):
    print('Running Comprehensive End-to-End Agent Test...')
    results = []
    correct_count = 0
    total = len(COMPREHENSIVE_QUESTIONS)
    async with httpx.AsyncClient() as client:
        for i, test_case in enumerate(COMPREHENSIVE_QUESTIONS):
            q = test_case['q']
            expected_source = test_case['source']
            keywords = test_case['keywords']
            print(f'Testing [{i + 1}/{total}]: {q}')
            req = {'employee_id': 'EMP001', 'question': q}
            try:
                resp = await client.post('http://127.0.0.1:8000/ask', json=req, timeout=30.0)
                resp.raise_for_status()
                data = resp.json()
                actual_answer = data['answer']
                actual_source = data['source']
                source_correct = expected_source is None or actual_source == expected_source
                keyword_correct = any((kw.lower() in actual_answer.lower() for kw in keywords))
                is_correct = source_correct and keyword_correct
                if is_correct:
                    correct_count += 1
                results.append({'question': q, 'answer': actual_answer, 'source': actual_source, 'expected_source': expected_source, 'is_correct': is_correct, 'error': None})
            except Exception as e:
                print(f'Error testing: {e}')
                results.append({'question': q, 'answer': f'Error: {str(e)}', 'source': 'error', 'expected_source': expected_source, 'is_correct': False, 'error': str(e)})
            await asyncio.sleep(5)
    os.makedirs('tests', exist_ok=True)
    with open('tests/comprehensive_results.md', 'w', encoding='utf-8') as f:
        f.write('# Automated Test Report\n\n')
        f.write(mrr_markdown)
        f.write('## Part 2: Comprehensive End-to-End Agent Test\n\n')
        percentage = correct_count / total * 100
        f.write(f'### **Final Score:** {correct_count} / {total} ({percentage:.1f}%)\n\n')
        for i, r in enumerate(results):
            status_icon = 'correct' if r['is_correct'] else 'wrong'
            f.write(f"### Q{i + 1}: {r['question']} {status_icon}\n")
            f.write(f"- **Agent Answer:** {r['answer']}\n")
            f.write(f"- **Actual Source:** `{r['source']}` (Expected: `{(r['expected_source'] if r['expected_source'] else 'Any')}`)\n")
            f.write('\n')
    print(f'\nDone! Score: {correct_count}/{total} ({percentage:.1f}%). Results saved to tests/comprehensive_results.md')
if __name__ == '__main__':
    mrr_output = evaluate_mrr()
    try:
        httpx.get('http://127.0.0.1:8000', timeout=1.0)
        asyncio.run(run_comprehensive_test(mrr_output))
    except httpx.RequestError:
        print('\nSkipping Part 2 (End-to-End Test) because the FastAPI server is not running on http://127.0.0.1:8000')
        print('To run the comprehensive test, start the server first: `uv run python -m main`')
        os.makedirs('tests', exist_ok=True)
        with open('tests/comprehensive_results.md', 'w', encoding='utf-8') as f:
            f.write('# Automated Test Report\n\n')
            f.write(mrr_output)
            f.write('\n*End-to-End tests skipped because server was offline.*\n')
