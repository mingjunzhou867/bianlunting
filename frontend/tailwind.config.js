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
                    strict: '#9F1D22',
                    lenient: '#1E5AA8',
                    explorer: '#C58B2B',
                    empirical: '#1E5AA8',
                    auditor: '#1E5AA8',
                }
            }
        },
    },
    plugins: [],
}
