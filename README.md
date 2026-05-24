# LeagueQL
[LeagueQL](https://leagueql.com/) is an app that helps fantasy football managers analyze their ESPN or Sleeper leagues. The app fetches data from the respective fantasy platform's API and transforms it into insights such as all-time records, year-to-year manager trends, best draft picks, and more.

# Tech Stack
- Fast API + Python (Backend)
- React + TypeScript (Frontend)
- Terraform + AWS (Infrastructure)
- Backend hosted on AWS API Gateway + Lambda
- Frontend hosted on Cloudflare Pages

# Current Features
- Season standings from each past + current season and season superlative awards
- All historical league matchups + box scores
- Playoff brackets from each season
- Head-to-head comparison of any two managers
- Year-to-year history of each manager's performance
- Recap of draft picks and grades
- All-time fantasy player performance records
- All-time fantasy team performance records
- League migration: track all-time metrics even if your fantasy league migrates platforms

# Roadmap
- Add support for additional platforms (e.g. Yahoo, NFL.com)
- Create a Chrome extension to auto-fill ESPN cookies
- Support leagues with auction drafts (the current draft page is designed for snake drafts)


# Contributing
All contributions are welcome! You can look through the existing issues or create your own. Create a feature branch from `main` and submit a pull request once you have implemented your changes. I will review once it passes all checks.

# Support
Report any bugs/issues in the [issues tab](https://github.com/amolrairikar/leagueql-app/issues) and I will try my best to address them when I can. Please note that this is a passion project and I may not be able to provide immediate support.