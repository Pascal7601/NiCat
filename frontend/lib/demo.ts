/** Visual preview data only: never saved or sent to Django. */
import type { Exam, Attempt, GradeResult, AttemptHistory } from './types';
export const demoExam: Exam = {
  id: '00000000-0000-4000-8000-000000000016', title: 'Data Structures & Algorithms — Practice CAT',
  unit_id: '00000000-0000-4000-8000-000000000021', duration_seconds: 1800,
  instructions: '12 questions · 20 marks · 30 minutes. Ten multiple-choice and two written questions.',
};
export const demoHistory: AttemptHistory[] = [
  { id: '00000000-0000-4000-8000-000000000051', status: 'graded_final', started_at: '2026-11-18T13:30:00Z' },
  { id: '00000000-0000-4000-8000-000000000052', status: 'grading_pending', started_at: '2026-11-16T08:00:00Z' },
];
export const demoAttempt: Attempt = {
  id: 'demo-attempt', status: 'in_progress', started_at: new Date().toISOString(),
  deadline_at: new Date(Date.now()+1800*1000).toISOString(), submitted_at: null,
  questions: [
    { id:'q1',position:1,kind:'single_choice',prompt:'Which data structure follows the Last In, First Out (LIFO) principle?',marks:'1.00',topic:'Stacks and queues',provenance:'independently_authored',response:null,options:[{id:'a',text:'Queue'},{id:'b',text:'Stack'},{id:'c',text:'Binary tree'},{id:'d',text:'Graph'}]},
    { id:'q2',position:2,kind:'single_choice',prompt:'What is the worst-case time complexity of a sequential search over n elements?',marks:'1.00',topic:'Searching',provenance:'independently_authored',response:null,options:[{id:'a',text:'O(1)'},{id:'b',text:'O(log n)'},{id:'c',text:'O(n)'},{id:'d',text:'O(n log n)'}]},
    { id:'q3',position:3,kind:'single_choice',prompt:'Which traversal visits a binary tree root before its subtrees?',marks:'1.00',topic:'Trees',provenance:'independently_authored',response:null,options:[{id:'a',text:'Inorder'},{id:'b',text:'Postorder'},{id:'c',text:'Preorder'},{id:'d',text:'Level-only'}]},
    { id:'q4',position:4,kind:'written',prompt:'Explain how binary search reduces the search space and state its time complexity.',marks:'5.00',topic:'Searching',provenance:'independently_authored',response:null,options:[]},
  ],
};
export const demoResult: GradeResult = {
  attempt_id:'demo-attempt', status:'grading_pending', scored_marks:'7.00', scored_possible_marks:'10.00', ungraded_possible_marks:'10.00', final_percentage:null,
  items:[{question_id:'q1',status:'final',awarded:'1.00',possible:'1.00',explanation:null,correct_answer:null},{question_id:'q2',status:'final',awarded:'0.00',possible:'1.00',explanation:null,correct_answer:null},{question_id:'q4',status:'pending_review',awarded:null,possible:'5.00',explanation:null,correct_answer:null}],
};
