/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow CI/release checks to use a clean output directory when a previous
  // container build left `.next` protected by macOS ACLs.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Hide the Next.js badge shown in the corner during development.
  devIndicators: false,
};

module.exports = nextConfig;
