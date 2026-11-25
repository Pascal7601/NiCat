import type { ReactNode } from 'react';
import StaffAccessGate from '@/components/staff/StaffAccessGate';
import './staff.css';

export default function StaffLayout({ children }: { children: ReactNode }) {
  return <StaffAccessGate>{children}</StaffAccessGate>;
}
