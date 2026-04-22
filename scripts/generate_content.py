#!/usr/bin/env python3
"""
Content generation script for portfolio sites.

Uses AI to generate initial content for portfolio pages based on the
writer's profile and the provided prompt templates.
"""

import os
import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, Optional

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

def load_config(config_path: str = "../../config.yaml") -> Dict:
    """Load configuration from YAML file or environment variables."""
    config = {}

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}

    if os.getenv('AI_PROVIDER'):
        config['ai_provider'] = os.getenv('AI_PROVIDER')
    if os.getenv('AI_API_KEY'):
        config['ai_api_key'] = os.getenv('AI_API_KEY')
    if os.getenv('AI_MODEL'):
        config['model'] = os.getenv('AI_MODEL')

    required_fields = ['ai_provider', 'ai_api_key', 'model']
    missing_fields = [
        f for f in required_fields
        if f not in config or not config[f] or config[f] == 'YOUR_API_KEY_HERE'
    ]

    if missing_fields:
        print(f"❌ Error: Missing required configuration: {', '.join(missing_fields)}")
        print(f"\nPlease update {config_path} with your API keys")
        print("Or set environment variables:")
        for field in missing_fields:
            print(f"  export {field.upper()}='your-value'")
        sys.exit(1)

    return config


def get_sample_profile() -> Dict:
    """Return a sample profile for testing without a profile file."""
    return {
        "name": "Jane Smith",
        "title": "Senior Technical Writer",
        "years_experience": 8,
        "specialties": ["API documentation", "Developer guides", "Process documentation"],
        "tools": ["MkDocs", "Confluence", "Git/GitHub", "Swagger/OpenAPI"],
        "experience": [
            {
                "company": "TechCorp",
                "role": "Senior Technical Writer",
                "years": "2021–present",
                "highlights": [
                    "Built developer portal from scratch, reducing support tickets by 30%",
                    "Managed docs-as-code migration for 50+ legacy documents",
                ]
            },
            {
                "company": "StartupCo",
                "role": "Technical Writer",
                "years": "2019–2021",
                "highlights": [
                    "Created first API reference documentation for REST APIs",
                    "Wrote onboarding guides adopted by 200+ users",
                ]
            }
        ],
        "approach": "I believe good documentation is invisible — it answers questions before they're asked.",
        "contact": {
            "email": "jane@example.com",
            "linkedin": "linkedin.com/in/janesmith",
        },
        "projects": [
            {
                "name": "Developer Portal",
                "description": "Company-wide developer documentation site for TechCorp's APIs",
                "challenge": "No central documentation existed; developers relied on tribal knowledge",
                "contribution": "Designed IA, wrote all API reference docs, created getting-started guides with working code examples",
                "tools": ["MkDocs", "OpenAPI", "GitHub Actions"],
                "outcome": "Reduced developer onboarding time from 2 weeks to 3 days",
            }
        ],
    }


def load_profile(profile_path: str) -> Dict:
    """Load writer profile from YAML file."""
    if not os.path.exists(profile_path):
        print(f"❌ Error: Profile file not found: {profile_path}")
        print(f"   Copy profile.example.yaml to profile.yaml and fill in your details")
        sys.exit(1)

    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)

    if not profile:
        print(f"❌ Error: Profile file is empty: {profile_path}")
        sys.exit(1)

    return profile


def format_profile(profile: Dict) -> str:
    """Format profile dictionary as readable text for AI prompts."""
    lines = []
    lines.append(f"Name: {profile.get('name', 'Not provided')}")
    lines.append(f"Title: {profile.get('title', 'Not provided')}")
    lines.append(f"Years of experience: {profile.get('years_experience', 'Not provided')}")

    if profile.get('specialties'):
        lines.append(f"\nSpecialties: {', '.join(profile['specialties'])}")

    if profile.get('tools'):
        lines.append(f"Tools: {', '.join(profile['tools'])}")

    if profile.get('experience'):
        lines.append("\nWork history:")
        for job in profile['experience']:
            lines.append(f"  - {job.get('role')} at {job.get('company')} ({job.get('years')})")
            for highlight in job.get('highlights', []):
                lines.append(f"    * {highlight}")

    if profile.get('approach'):
        lines.append(f"\nDocumentation philosophy: {profile['approach']}")

    return "\n".join(lines)


def format_project(project: Dict) -> str:
    """Format a single project as readable text for AI prompts."""
    lines = []
    lines.append(f"Project name: {project.get('name', 'Not provided')}")
    lines.append(f"Description: {project.get('description', 'Not provided')}")

    if project.get('challenge'):
        lines.append(f"Challenge: {project['challenge']}")
    if project.get('contribution'):
        lines.append(f"Contribution: {project['contribution']}")
    if project.get('tools'):
        lines.append(f"Tools used: {', '.join(project['tools'])}")
    if project.get('outcome'):
        lines.append(f"Outcome: {project['outcome']}")

    return "\n".join(lines)


def load_prompt(prompt_path: str) -> str:
    """Load a prompt template from file."""
    if not os.path.exists(prompt_path):
        print(f"❌ Error: Prompt file not found: {prompt_path}")
        print(f"   Make sure you're running from the 02-doc-site-portfolio/ directory")
        sys.exit(1)

    with open(prompt_path, 'r') as f:
        return f.read()


def call_ai(prompt: str, config: Dict) -> str:
    """Send a prompt to the configured AI provider and return the response."""
    provider = config['ai_provider'].lower()

    try:
        if provider == 'anthropic':
            if not HAS_ANTHROPIC:
                print("❌ Error: Anthropic library not installed. Run: pip install anthropic")
                sys.exit(1)

            client = anthropic.Anthropic(api_key=config['ai_api_key'])
            message = client.messages.create(
                model=config['model'],
                max_tokens=2000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

        elif provider == 'openai':
            if not HAS_OPENAI:
                print("❌ Error: OpenAI library not installed. Run: pip install openai")
                sys.exit(1)

            client = openai.OpenAI(api_key=config['ai_api_key'])
            response = client.chat.completions.create(
                model=config['model'],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.4
            )
            return response.choices[0].message.content

        else:
            print(f"❌ Error: Unknown AI provider: {provider}")
            print("   Supported providers: anthropic, openai")
            sys.exit(1)

    except Exception as e:
        print(f"❌ AI API Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API key is valid")
        print("2. Verify billing is set up (after free tier)")
        print("3. Check rate limits")
        sys.exit(1)


def generate_about_page(profile: Dict, config: Dict, prompts_dir: str) -> str:
    """Generate About page content from writer profile."""
    prompt_template = load_prompt(os.path.join(prompts_dir, "about_page_prompt.txt"))
    prompt = prompt_template.replace("{PROFILE}", format_profile(profile))
    return call_ai(prompt, config)


def generate_home_page(profile: Dict, config: Dict) -> str:
    """Generate homepage content from writer profile."""
    project_names = [p.get('name') for p in profile.get('projects', []) if p.get('name')]
    featured = "\n".join(f"- {name}" for name in project_names[:3]) if project_names else "- (Add your featured projects here)"

    contact = profile.get('contact', {})
    contact_line = contact.get('email') or contact.get('linkedin') or "See the Contact page"

    prompt = f"""You are helping a technical writer create a homepage for their portfolio site.

Based on the following profile, write a welcoming homepage in Markdown format.
Write in the first person. Keep it brief — this is an introduction, not a full resume.

PROFILE:
{format_profile(profile)}

Write content for these sections:

## Welcome
A 2-sentence welcome that tells visitors who you are and what they'll find here.

## Featured Projects
A 2–3 bullet list highlighting their strongest work. Use these project names if available:
{featured}

## Get in Touch
One sentence with their preferred contact method ({contact_line}).

Requirements:
- Warm and professional tone
- Brief — the homepage should invite exploration, not tell everything
- Do not include placeholder text
- Output valid Markdown only
"""
    return call_ai(prompt, config)


def generate_project_page(profile: Dict, project_name: str, config: Dict, prompts_dir: str) -> str:
    """Generate a project showcase page for a named project."""
    projects = profile.get('projects', [])
    project = next(
        (p for p in projects if p.get('name', '').lower() == project_name.lower()),
        None
    )

    if not project:
        available = [p.get('name', '') for p in projects]
        print(f"❌ Error: Project '{project_name}' not found in profile")
        if available:
            print(f"   Available projects: {', '.join(available)}")
        else:
            print("   No projects found in profile. Add a 'projects' section to your profile YAML.")
        sys.exit(1)

    prompt_template = load_prompt(os.path.join(prompts_dir, "project_page_prompt.txt"))
    prompt = prompt_template.replace("{PROJECT_INFO}", format_project(project))
    prompt = prompt.replace("{PROFILE}", format_profile(profile))
    return call_ai(prompt, config)


def generate_site_structure(profile: Dict, config: Dict, prompts_dir: str) -> str:
    """Generate a recommended site nav structure."""
    prompt_template = load_prompt(os.path.join(prompts_dir, "site_structure_prompt.txt"))
    prompt = prompt_template.replace("{PROFILE}", format_profile(profile))
    return call_ai(prompt, config)


def wrap_output(content: str, page_type: str) -> str:
    """Add a review disclaimer to generated content."""
    disclaimer = "\n\n---\n\n_Generated using AI-assisted automation. Please review for accuracy before publishing._\n"
    return content + disclaimer


def main():
    parser = argparse.ArgumentParser(
        description='Generate portfolio site content using AI',
        epilog='Example: python generate_content.py --page about --profile my_profile.yaml'
    )
    parser.add_argument(
        '--page',
        required=True,
        choices=['about', 'home', 'project', 'structure'],
        help='Which page to generate: about, home, project, or structure (site nav)'
    )
    parser.add_argument('--profile', default='profile.yaml', help='Path to profile YAML file')
    parser.add_argument('--project', help='Project name to generate (required when --page project)')
    parser.add_argument('--output', help='Output file path (prints to stdout if not specified)')
    parser.add_argument('--prompts-dir', default='prompts', help='Directory containing prompt templates')
    parser.add_argument('--config', default='../../config.yaml', help='Config file path')
    parser.add_argument('--sample', action='store_true', help='Use sample profile data instead of a profile file')

    args = parser.parse_args()

    if args.page == 'project' and not args.project:
        print("❌ Error: --project is required when --page is 'project'")
        print("   Example: --page project --project 'Developer Portal'")
        sys.exit(1)

    if not HAS_ANTHROPIC and not HAS_OPENAI:
        print("❌ Error: No AI provider library installed")
        print("   Run: pip install anthropic   (for Claude)")
        print("   or:  pip install openai      (for GPT)")
        sys.exit(1)

    print("✍️  Portfolio Content Generator")
    print("=" * 50)

    config = load_config(args.config)

    if args.sample:
        print("Using sample profile (no profile file needed)")
        profile = get_sample_profile()
    else:
        print(f"\n📋 Loading profile from {args.profile}...")
        profile = load_profile(args.profile)
        print(f"✓ Loaded profile for {profile.get('name', 'unknown')}")

    print(f"\n🤖 Generating '{args.page}' page using {config['ai_provider'].upper()} ({config['model']})...")

    if args.page == 'about':
        content = generate_about_page(profile, config, args.prompts_dir)
    elif args.page == 'home':
        content = generate_home_page(profile, config)
    elif args.page == 'project':
        content = generate_project_page(profile, args.project, config, args.prompts_dir)
    elif args.page == 'structure':
        content = generate_site_structure(profile, config, args.prompts_dir)

    print("✓ Content generated")

    # Add disclaimer to page content (not to the structure/YAML output)
    output = wrap_output(content, args.page) if args.page != 'structure' else content

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(output)
        print(f"✓ Written to {args.output}")
    else:
        print("\n" + "=" * 50)
        print(output)
        print("=" * 50)
        print("\n💡 Tip: Use --output to write directly to a file")

    print("\n✅ Done! Review the output and personalize any details.")
    print("\n💡 Next steps:")
    print("   1. Read through the generated content carefully")
    print("   2. Update anything that doesn't sound like you")
    print("   3. Add specific details the AI couldn't know")
    if args.page != 'structure':
        print(f"   4. Run improve_content.py to refine further")


if __name__ == "__main__":
    main()
