# Project Repository

This repository is maintained as a single shared GitHub repository for the project team and is expected to follow the standard structure defined for this unit.

## Strict repository guideline

The project repository shall:

- Be maintained as one shared GitHub repository per project team.
- Follow the standard repository structure defined for this unit.
- Store GitHub Actions workflow files in the .github/workflows/ directory.
- Store project documentation, architecture diagrams, and reports in the docs/ directory.
- Store the project overview and setup instructions in README.md.
- Store version control exclusions in .gitignore.
- Store the Docker Compose configuration in docker-compose.yml.
- Store the integrated home page, shared CSS, JavaScript, assets, and common configuration in the shared/ directory.
- Store each student's assigned frontend, backend/API, database, testing, and Docker artefacts in their designated student-x/ directory.
- Store the shared AI services in the ai-services/ directory.
- Store project build, testing, and deployment scripts in the scripts/ directory.
- Integrate all individual student microservices into one working software application.
- Execute the integrated application locally using the shared docker-compose.yml configuration.
- Maintain one shared Docker Compose configuration for the entire project team.
- Maintain one shared cloud deployment for the integrated application.
- Deploy the complete integrated application, not individual student microservices.
- Deploy the integrated application to either Microsoft Azure or Amazon Web Services (AWS).
- Require each student to integrate and validate their assigned microservices before cloud deployment.
- Require the project team to maintain the integrated software architecture, Docker configuration, and cloud deployment configuration.
- Maintain a clear separation between individual student components and shared project components.

## Repository structure

- .github/workflows/ - GitHub Actions automation and CI/CD definitions.
- docs/ - project documentation, architecture diagrams, and reports.
- shared/ - shared frontend, CSS, JavaScript, assets, and common configuration.
- student-1/ through student-5/ - student-specific frontend, backend, database, testing, and Docker artefacts.
- ai-services/ - shared AI service components and integrations.
- scripts/ - build, testing, and deployment automation.
- docker-compose.yml - single shared local orchestration file for the integrated application.
- README.md - repository overview, setup guidance, and team reference.
- .gitignore - repository exclusions and local environment settings.

## Local setup

1. Review the repository structure before making changes.
2. Keep shared components separate from student-specific components.
3. Use the shared docker-compose.yml file to run the integrated application locally.
4. Validate each student microservice before team integration.
5. Keep deployment and documentation aligned with the integrated application, not isolated student services.

## Notes for agents

This repository is intended to be a single team-owned project. Preserve the separation between shared project assets and individual student work. Do not deploy or document individual student microservices independently when the requirement is to deploy the integrated application as a whole.
