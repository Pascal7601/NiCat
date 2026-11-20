/** Preview mode must never be used with student data or in production. */
export const isDemo = process.env.NODE_ENV !== 'production' && process.env.NEXT_PUBLIC_NICAT_DEMO_MODE === 'true';
