#!/usr/bin/env python3
"""
Content improvement script for portfolio sites.

Uses AI to review and refine existing Markdown content for clarity,
consistency, and professional presentation.
"""

import os
import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict

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

FOCUS_DESCRIPTIONS = {
    "clarity": (
        "Make the writing clearer and easier to understand. "
        "Simplify complex sentences, remove jargon, and ensure each section has a clear purpose."
    ),
    "tone": (
        "Make the tone more professional and confident. "
        "Remove hedging language, passive voice, and generic claims. "
        "Ensure it reads like a skilled practitioner speaking about their work."
    ),
    "consistency": (
        "Ensure consistent voice, tense, and formatting throughout. "
        "Standardize heading levels, list styles, and terminology."
    ),
    "all": (
        "Improve clarity, professional tone, and consistency throughout. "
        "Simplify complex sentences, strengthen the voice, and standardize formatting."
    ),
}


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


def get_sample_content() -> str:
    """Return sample portfolio content for testing without a real file."""
    return """# About Me

I am a technical writer with experience in many areas of documentation. I have worked at
several companies over the years and have done a lot of different writing projects.

## Skills

I know how to use various tools including MkDocs, Confluence, and Git. I also have experience
with API documentation and other kinds of technical writing.

## Experience

At my previous job I worked on documentation for a software company. I wrote user guides and
API documentation and other things. I also helped with the documentation process.

## My Approach

I think documentation should be clear and helpful. I try to make sure that users can find
what they need and understand it. I believe in working closely with developers to make sure
the documentation is accurate.
"""


def read_content(file_path: str) -> str:
    """Read Markdown content from a file."""
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    with open(file_path, 'r') as f:
        return f.read()


def build_improvement_prompt(content: str, focus: str) -> str:
    """Build the improvement prompt for the given content and focus area."""
    focus_instruction = FOCUS_DESCRIPTIONS.get(focus, FOCUS_DESCRIPTIONS["all"])

    return f"""You are a writing editor helping a technical writer improve their portfolio content.

Review the following Markdown content and rewrite it to be stronger.

FOCUS: {focus_instruction}

CONTENT TO IMPROVE:
{content}

Rules:
- Preserve the existing Markdown structure (headings, lists, etc.)
- Do not add information that isn't already present or implied
- Do not remove sections — improve them
- Keep the writer's voice; just make it stronger and clearer
- Output the improved Markdown only, with no commentary or explanation
"""


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
                temperature=0.3,
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
                temperature=0.3
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


def main():
    parser = argparse.ArgumentParser(
        description='Improve existing portfolio content using AI',
        epilog='Example: python improve_content.py --file template/docs/about.md'
    )
    parser.add_argument('--file', help='Path to the Markdown file to improve')
    parser.add_argument(
        '--focus',
        default='all',
        choices=['clarity', 'tone', 'consistency', 'all'],
        help='What to focus on: clarity, tone, consistency, or all (default: all)'
    )
    parser.add_argument(
        '--output',
        help='Output file path (defaults to overwriting the input file)'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Print improved content to stdout without writing to a file'
    )
    parser.add_argument('--config', default='../../config.yaml', help='Config file path')
    parser.add_argument('--sample', action='store_true', help='Use sample content instead of a file')

    args = parser.parse_args()

    if not HAS_ANTHROPIC and not HAS_OPENAI:
        print("❌ Error: No AI provider library installed")
        print("   Run: pip install anthropic   (for Claude)")
        print("   or:  pip install openai      (for GPT)")
        sys.exit(1)

    if not args.sample and not args.file:
        print("❌ Error: Provide --file or use --sample for testing")
        parser.print_help()
        sys.exit(1)

    print("✨ Portfolio Content Improver")
    print("=" * 50)

    config = load_config(args.config)

    if args.sample:
        print("Using sample content (no file needed)")
        content = get_sample_content()
        source_path = None
    else:
        print(f"\n📄 Reading {args.file}...")
        content = read_content(args.file)
        source_path = args.file
        print(f"✓ Loaded {len(content)} characters")

    print(f"\n🤖 Improving content (focus: {args.focus}) using {config['ai_provider'].upper()} ({config['model']})...")

    prompt = build_improvement_prompt(content, args.focus)
    improved = call_ai(prompt, config)
    print("✓ Improvement complete")

    disclaimer = "\n\n---\n\n_Reviewed and refined using AI-assisted automation. Please verify all details are accurate._\n"
    output = improved + disclaimer

    if args.preview:
        print("\n" + "=" * 50)
        print(output)
        print("=" * 50)
        print("\n💡 Remove --preview to write the changes to a file")
    else:
        output_path = args.output or source_path
        if not output_path:
            # sample mode with no --output: print to stdout
            print("\n" + "=" * 50)
            print(output)
            print("=" * 50)
        else:
            with open(output_path, 'w') as f:
                f.write(output)
            print(f"✓ Written to {output_path}")

    print("\n✅ Done! Review the changes and adjust anything that doesn't sound like you.")
    print("\n💡 Next steps:")
    print("   1. Read through the improved content")
    print("   2. Revert any changes that don't feel right")
    print("   3. Add specific details the AI couldn't know")
    print("   4. Run again with a different --focus if needed")


if __name__ == "__main__":
    main()
