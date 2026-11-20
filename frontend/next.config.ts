import type { NextConfig } from "next";

if (
    process.env.NODE_ENV === "production" &&
    process.env.NEXT_PUBLIC_NICAT_DEMO_MODE === "true"
) {
    throw new Error("NiCat production builds must disable demo mode.");
}

const config: NextConfig = {
    reactStrictMode: true,
    poweredByHeader: false,
    output: "standalone",
};

export default config;
