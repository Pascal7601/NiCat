'use client';

import Link from 'next/link';
import StaffFrame from '@/components/staff/StaffFrame';
import QuestionBrowser from '@/components/staff/QuestionBrowser';

export default function StaffQuestionBank() {
  return (
    <StaffFrame title="Published question bank" description="Browse NiCat's approved, published practice questions by programme, unit and topic. Question generation is planned for Sprint 14.">
      <QuestionBrowser />
      <p className="muted tiny" style={{ marginTop: 16 }}>
        To generate a reviewer-approved explanation for one of these questions, open <Link href="/staff/tutor">AI Tutor Review</Link>. This browser does not publish, edit or create questions.
      </p>
    </StaffFrame>
  );
}
