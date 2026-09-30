-- Seed data migrated from the previous static frontend (hardcoded project
-- cards and the `certificates` array in script.js). Paths are relative to
-- frontend/index.html (the site root once deployed to GitHub Pages).
-- The admin user is NOT seeded here: it is created automatically on backend
-- startup from ADMIN_EMAIL / ADMIN_PASSWORD so no password hash is ever
-- committed to the repo.

INSERT INTO projects (title, description, technologies, category, featured) VALUES
('Innovative AI',
 'An AI-powered platform that helps developers understand GitHub repositories: it reads a repo, generates plain-language explanations of what the code does, and builds a personalized learning roadmap from it.',
 'Python,AI,LLMs', 'AI Platform', TRUE),
('AI Concierge for ET',
 'An AI concierge built for the ET AI Hackathon that provides personalized financial insights and recommendations based on user input.',
 'JavaScript,AI', 'Fintech AI', TRUE),
('SplitterEase',
 'An expense-splitter application supporting equal splits and exact splits, with debt simplification handled by a greedy algorithm so groups settle up in the fewest possible transactions.',
 'Python', 'Utility', TRUE),
('Railway Reservation System',
 'A ticket-booking system covering search, booking and cancellation flows, built in C to work directly with core data structures and file handling.',
 'C', 'Systems', TRUE),
('Laptop Recovery System',
 'A security-focused application designed to help recover lost or stolen laptops, written in C.',
 'C', 'Security', TRUE);

INSERT INTO certificates (title, issuer, image_url, pdf_url) VALUES
('Azure Fundamentals', 'Microsoft', 'assets/logos/Microsoft Logo.jpg', 'certificates/Azure Fundamental(Az-900).pdf'),
('Azure AI Fundamentals', 'Microsoft', 'assets/logos/Microsoft Logo.jpg', 'certificates/Ai-900-Certificate.pdf'),
('AI Fundamentals', 'IBM', 'assets/logos/Ibm Logo.jpg', 'certificates/Artificial Intelligence Fundamentals(IBM).pdf'),
('Oracle Cloud Infrastructure AI Foundations Associate', 'OCI', 'assets/logos/Oracle Logo.jpg', 'certificates/oracle.pdf'),
('Gen AI Engineering Mastermind', 'Outskill', 'assets/logos/Outskill Logo.jpg', 'certificates/Outskill_Certificate.pdf'),
('Web Development Fundamental', 'IBM', 'assets/logos/Ibm Logo.jpg', 'certificates/Web Devlopment Fundamental.pdf'),
('Enterprise Design Thinking Practitioner', 'IBM', 'assets/logos/Ibm Logo.jpg', 'certificates/EnterpriseDesignThinkingPractitioner.pdf'),
('Prompt Engineering', 'IBM', 'assets/logos/Ibm Logo.jpg', 'certificates/IBM Prompt Engineering Certificate.pdf'),
('Python (Basic) - HackerRank', 'HackerRank', 'assets/logos/HackerRank Logo.jpg', 'certificates/python_basic certificate.pdf');
