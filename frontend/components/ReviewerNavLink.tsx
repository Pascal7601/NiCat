
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ClipboardCheck } from 'lucide-react';
import { clientRequest, route } from '@/lib/client';
import { isDemo } from '@/lib/preview';
import type { User } from '@/lib/types';

export default function ReviewerNavLink({
  selected,
}: {
  selected: boolean;
}) {
  const [canReview, setCanReview] = useState(false);

  useEffect(() => {
    if (isDemo) return;

    let active = true;

    clientRequest<User>(route.me)
      .then((user) => {
        if (active) {
          setCanReview(user.can_review_written);
        }
      })
      .catch(() => {
        if (active) {
          setCanReview(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  if (!canReview) return null;

  return (
    <Link
      href="/review"
      className={`nav-link ${selected ? 'selected' : ''}`}
      aria-current={selected ? 'page' : undefined}
    >
      <ClipboardCheck size={18} aria-hidden="true" />
      Review answers
    </Link>
  );
}
