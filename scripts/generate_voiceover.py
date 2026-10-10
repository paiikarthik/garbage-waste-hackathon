"""
EcoTrack System Architecture & Design Voiceover Generator
Uses gTTS (Google Text-to-Speech) to generate MP3 voice tracks for each slide
and a concatenated full audio walkthrough.
"""

import os
import sys
from pathlib import Path
from gtts import gTTS

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

# Scene-by-scene narrated scripts tailored for video presentation and pitch
SLIDE_SCRIPTS = {
    1: {
        "filename": "slide_01_title_and_vision.mp3",
        "title": "Slide 1: Title & Architectural Vision",
        "duration_est": "25 sec",
        "text": (
            "Welcome everyone! Today we are presenting the technical architecture and system design of EcoTrack. "
            "EcoTrack is a full-stack, smart waste management platform built to bridge the gap between citizen complaints "
            "and civic community action. In this walkthrough, we will explore our decoupled four-tier service model, "
            "our lightweight offline computer vision pipeline, relational ACID-compliant data schemas, and our production scalability roadmap."
        )
    },
    2: {
        "filename": "slide_02_high_level_architecture.mp3",
        "title": "Slide 2: 4-Tier High-Level Architecture",
        "duration_est": "35 sec",
        "text": (
            "Here is the high-level system architecture. Our Client Tier is an ultra-fast Vanilla ES6 Single Page Application "
            "under 75 kilobytes with zero build overhead, communicating via REST with our Python 3 FastAPI backend. "
            "Our AI Engine analyzes images and spatial data locally without external paid cloud dependencies. "
            "Finally, our Persistence Tier stores data in a normalized SQLite database with foreign key cascading, "
            "while static assets are served from an isolated UUID-hashed uploads directory."
        )
    },
    3: {
        "filename": "slide_03_ai_vision_and_algorithms.mp3",
        "title": "Slide 3: AI Computer Vision & Heuristic Algorithms",
        "duration_est": "35 sec",
        "text": (
            "Let's dive into our AI and algorithmic design. Rather than sending citizen photos to costly external cloud APIs, "
            "our embedded Computer Vision pipeline computes RGB luminance, channel variance, and texture standard deviations "
            "to classify waste into categories like plastic, organic, or e-waste in under 40 milliseconds. "
            "Simultaneously, our Neighborhood Cleanliness Index algorithm calculates a live civic health score "
            "and dynamically optimizes green walking routes away from active garbage hotspots."
        )
    },
    4: {
        "filename": "slide_04_reporting_data_lifecycle.mp3",
        "title": "Slide 4: Reporting Lifecycle & Gamification Sequence",
        "duration_est": "35 sec",
        "text": (
            "This sequence diagram illustrates our waste reporting and gamification transaction lifecycle. "
            "When a citizen uploads a photo, the image is sanitized and classified. The FastAPI gateway executes a database transaction "
            "that creates a unique tracking ID, awards 10 points to the user, logs an immutable audit record to the points log, "
            "checks for milestone badge unlocks, and broadcasts real-time in-app notifications to keep volunteers engaged."
        )
    },
    5: {
        "filename": "slide_05_relational_schema_design.mp3",
        "title": "Slide 5: Data Engineering & Relational Schema",
        "duration_est": "30 sec",
        "text": (
            "Our persistence layer consists of 12 normalized relational tables with foreign key constraints and indexed lookup fields. "
            "We maintain tables for users, waste reports, cleanup drives, participant attendance, community discussion posts, "
            "and verifiable certificates. This structure guarantees complete transactional consistency, zero duplicate records, "
            "and sub-5 millisecond query latency on local machines."
        )
    },
    6: {
        "filename": "slide_06_security_and_resilience.mp3",
        "title": "Slide 6: Security, Auth & Fault Tolerance",
        "duration_est": "30 sec",
        "text": (
            "Security is built into every layer. We utilize stateless HS256 JSON Web Tokens with seven-day lifespans, "
            "salted SHA-256 password hashing, and strict role-based access control distinguishing everyday citizens from municipal administrators. "
            "Our ASGI security middleware injects strict browser protection headers, including X-Frame-Options, "
            "X-Content-Type-Options, and Cross-Site Scripting filters to prevent common web exploits."
        )
    },
    7: {
        "filename": "slide_07_scalability_and_roadmap.mp3",
        "title": "Slide 7: Production Scalability & Conclusion",
        "duration_est": "30 sec",
        "text": (
            "Finally, looking at our production scalability roadmap: EcoTrack's modular architecture scales effortlessly "
            "to thousands of concurrent users. In production, SQLite can seamlessly migrate to AWS Aurora PostgreSQL with PostGIS "
            "for geo-spatial indexing, static media offloaded to Amazon S3 or Cloudflare R2, and Redis integrated for caching real-time leaderboards. "
            "EcoTrack combines clean engineering, fast algorithms, and civic gamification to build sustainable cities. Thank you!"
        )
    }
}

async def synthesize_speech(text: str, output_path: str, voice: str = "en-IN-PrabhatNeural"):
    """Synthesizes speech using edge-tts (Microsoft Neural Voice)."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice=voice, rate="+0%", pitch="+0Hz")
        await communicate.save(str(output_path))
        return True
    except Exception as e:
        print(f"   [Notice] edge-tts error ({e}), falling back to gTTS...")
        from gtts import gTTS
        tts = gTTS(text=text, lang="en", tld="co.in", slow=False)
        tts.save(str(output_path))
        return True

async def generate_voiceovers_async(voice: str = "en-IN-PrabhatNeural", overwrite: bool = True):
    print("=" * 60)
    print(f">> EcoTrack System Design Voiceover Generator")
    print(f">> Voice: {voice} (Natural Indian English Male Voice)")
    print(f">> Saving audio files to: {AUDIO_DIR.resolve()}")
    print("=" * 60)

    full_text_chunks = []

    for slide_num, data in SLIDE_SCRIPTS.items():
        file_path = AUDIO_DIR / data["filename"]
        print(f"\n[Slide {slide_num}/7] Generating: {data['title']} in Male Indian Accent...")
        print(f"   Target file: {data['filename']} (Est: {data['duration_est']})")
        
        # Check if already generated and not overwrite
        if not overwrite and file_path.exists() and os.path.getsize(file_path) > 1000:
            print(f"   [OK] Already generated: {file_path.name} ({os.path.getsize(file_path):,} bytes)")
            full_text_chunks.append(data["text"])
            continue

        # Synthesize audio with edge-tts
        for attempt in range(3):
            try:
                await synthesize_speech(data["text"], str(file_path), voice=voice)
                print(f"   [OK] Saved Male Voice track: {file_path.name} ({os.path.getsize(file_path):,} bytes)")
                break
            except Exception as e:
                if attempt == 2:
                    print(f"   [ERROR] Failed to generate {file_path.name}: {e}")
                    raise
                import asyncio
                await asyncio.sleep(2)
        
        full_text_chunks.append(data["text"])

    # Generate full concatenated voiceover
    full_audio_path = AUDIO_DIR / "full_system_design_voiceover.mp3"
    print("\n" + "-" * 60)
    print(">> Generating Complete Continuous Walkthrough Audio in Male Indian Accent...")
    combined_script = " ... \n\n ".join(full_text_chunks)
    
    try:
        await synthesize_speech(combined_script, str(full_audio_path), voice=voice)
        print(f"[OK] Full walkthrough audio saved: {full_audio_path.name} ({os.path.getsize(full_audio_path):,} bytes)")
    except Exception as e:
        print(f"[WARN] Could not generate combined full track ({e}). Individual slide MP3s are ready.")

    print("=" * 60)
    print(">> All Male Indian Accent voiceover tracks successfully generated!")

def generate_voiceovers(voice="en-IN-PrabhatNeural", overwrite=True):
    import asyncio
    asyncio.run(generate_voiceovers_async(voice=voice, overwrite=overwrite))

if __name__ == "__main__":
    generate_voiceovers(voice="en-IN-PrabhatNeural", overwrite=True)
