/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                agent: {
                    strict: '#ef4444',     // red-500
                    lenient: '#10b981',    // emerald-500
                    explorer: '#f59e0b',   // amber-500
                    empirical: '#3b82f6',  // blue-500
                    auditor: '#8b5cf6',    // violet-500
                }
            }
        },
    },
    plugins: [],
}
