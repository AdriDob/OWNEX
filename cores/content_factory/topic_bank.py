"""Topic Bank Service - Manages the bank of video topics for Science Curiosity niche."""

from __future__ import annotations

from cores.content_factory.models import VideoTopic, VideoTopicStatus


class TopicBankService:
    """Manages the topic bank for Science Curiosity videos."""

    # Science Curiosity topic categories
    CATEGORIES = [
        "space_astronomy",
        "physics_phenomena",
        "biology_evolution",
        "earth_geology",
        "chemistry_reactions",
        "technology_future",
        "human_body",
        "nature_animals",
        "ocean_mysteries",
        "quantum_weirdness",
    ]

    # Seed topics for Science Curiosity (English, global appeal)
    SEED_TOPICS = [
        # Space & Astronomy
        {
            "title": "Why Venus Spins Backwards",
            "hook": "Every planet spins counter-clockwise... except Venus.",
            "insight": "Venus rotates clockwise, likely due to a massive collision early in its history that flipped its rotation.",
            "keywords": ["venus", "rotation", "planet", "solar system", "collision"],
            "category": "space_astronomy",
        },
        {
            "title": "The Star That Shouldn't Exist",
            "hook": "A star 200x larger than our Sun that defies physics.",
            "insight": "Stephenson 2-18 is so large it would swallow Jupiter's orbit. It challenges our understanding of stellar limits.",
            "keywords": ["stephenson 2-18", "red supergiant", "largest star", "astronomy"],
            "category": "space_astronomy",
        },
        {
            "title": "The Great Attractor: What's Pulling Our Galaxy?",
            "hook": "Something massive is pulling the Milky Way at 600 km/s.",
            "insight": "The Great Attractor is a gravitational anomaly 250 million light-years away. We can't see it directly due to the Zone of Avoidance.",
            "keywords": ["great attractor", "milky way", "gravity", "dark matter"],
            "category": "space_astronomy",
        },
        {
            "title": "Rogue Planets: Worlds Without Stars",
            "hook": "Billions of planets drift alone in the darkness between stars.",
            "insight": "Rogue planets were ejected from their solar systems. There may be more rogue planets than stars in the galaxy.",
            "keywords": ["rogue planets", "exoplanets", "interstellar", "ejected planets"],
            "category": "space_astronomy",
        },
        {
            "title": "The Moon Is Slowly Drifting Away",
            "hook": "Every year, the Moon moves 3.8 cm further from Earth.",
            "insight": "Tidal forces transfer Earth's rotational energy to the Moon's orbit. In 50 billion years, they'd be tidally locked.",
            "keywords": ["moon", "earth", "tidal forces", "orbital mechanics"],
            "category": "space_astronomy",
        },
        # Physics Phenomena
        {
            "title": "Why Water Boils Faster on Mount Everest",
            "hook": "At the summit, water boils at 71°C instead of 100°C.",
            "insight": "Lower atmospheric pressure reduces the energy needed for water molecules to escape as vapor. You can't cook pasta properly up there.",
            "keywords": ["boiling point", "atmospheric pressure", "mount everest", "physics"],
            "category": "physics_phenomena",
        },
        {
            "title": "The Leidenfrost Effect: Water That Floats on Fire",
            "hook": "Water droplets can skate across a surface hotter than their boiling point.",
            "insight": "A vapor layer forms under the droplet, insulating it from the hot surface. It's like a hovercraft made of steam.",
            "keywords": ["leidenfrost effect", "physics", "water", "surface tension"],
            "category": "physics_phenomena",
        },
        {
            "title": "Sonic Boom: Breaking the Sound Barrier",
            "hook": "The crack isn't from the plane—it's from the air itself.",
            "insight": "Pressure waves stack up into a shock wave cone. You hear it after the plane passes because the sound travels slower than the plane.",
            "keywords": ["sonic boom", "sound barrier", "shock wave", "physics"],
            "category": "physics_phenomena",
        },
        {
            "title": "Why Glass Is Actually a Liquid (Sort Of)",
            "hook": "Old window panes are thicker at the bottom—proof glass flows.",
            "insight": "Actually a myth! Glass is an amorphous solid. The uneven thickness is from primitive manufacturing. But amorphous solids DO have liquid-like disordered structure.",
            "keywords": ["glass", "amorphous solid", "physics", "myth busting"],
            "category": "physics_phenomena",
        },
        # Biology & Evolution
        {
            "title": "The Immortal Jellyfish",
            "hook": "Turritopsis dohrnii can revert to childhood after reaching maturity.",
            "insight": "When stressed, it transforms its cells back to polyp stage. It's the only known biologically immortal animal.",
            "keywords": ["turritopsis dohrnii", "immortal", "jellyfish", "biology", "regeneration"],
            "category": "biology_evolution",
        },
        {
            "title": "Trees Talk to Each Other Through Fungi",
            "hook": "Forests have an underground internet made of fungi.",
            "insight": "Mycorrhizal networks connect tree roots. Trees share nutrients, warn of pests, and even nurture seedlings through this 'Wood Wide Web'.",
            "keywords": ["mycorrhizal network", "wood wide web", "fungi", "trees", "symbiosis"],
            "category": "biology_evolution",
        },
        {
            "title": "The Octopus Has Three Hearts and Blue Blood",
            "hook": "Two hearts pump to gills, one to the body. Blood uses copper, not iron.",
            "insight": "Hemocyanin (copper-based) is more efficient in cold, low-oxygen water. When they swim, the systemic heart stops—so they prefer crawling.",
            "keywords": ["octopus", "hearts", "blue blood", "hemocyanin", "marine biology"],
            "category": "biology_evolution",
        },
        {
            "title": "Tardigrades: The Indestructible Micro-Animals",
            "hook": "They survive space vacuum, radiation, boiling, freezing, and 30 years without water.",
            "insight": "They enter cryptobiosis—expelling 97% of body water and replacing it with protective proteins. Their DNA has unique damage-suppression proteins.",
            "keywords": ["tardigrade", "water bear", "cryptobiosis", "extremophile", "space"],
            "category": "biology_evolution",
        },
        # Earth & Geology
        {
            "title": "The Moving Rocks of Death Valley",
            "hook": "Rocks weighing 300kg slide across the desert floor, leaving trails.",
            "insight": "Thin ice sheets form at night. Morning sun melts the bottom, creating a slippery surface. Wind pushes the rocks across the mud.",
            "keywords": ["sailing stones", "death valley", "geology", "mystery solved"],
            "category": "earth_geology",
        },
        {
            "title": "The Door to Hell: Burning for 50+ Years",
            "hook": "A crater in Turkmenistan has been burning since 1971.",
            "insight": "Soviet geologists accidentally hit a methane cavern. They lit it to prevent gas spread, expecting it to burn out in weeks. It's still going.",
            "keywords": ["door to hell", "darvaza crater", "methane", "turkmenistan"],
            "category": "earth_geology",
        },
        {
            "title": "Earth's Hum: The Planet Sings a Secret Song",
            "hook": "Earth vibrates at frequencies too low for human hearing—constantly.",
            "insight": "Ocean waves, atmospheric pressure, and seismic activity create a continuous hum between 2-7 millihertz. We only detected it in 1998.",
            "keywords": ["earth hum", "seismic", "infrasound", "planet earth"],
            "category": "earth_geology",
        },
        # Chemistry & Reactions
        {
            "title": "The Most Violent Chemical Reaction: Thermite",
            "hook": "Iron oxide + aluminum = 2500°C, melting through engine blocks.",
            "insight": "Aluminum steals oxygen from iron oxide in a spectacular redox reaction. Used for welding train tracks underwater.",
            "keywords": ["thermite", "chemical reaction", "aluminum", "iron oxide", "welding"],
            "category": "chemistry_reactions",
        },
        {
            "title": "Gallium: The Metal That Melts in Your Hand",
            "hook": "A metal that's solid at room temperature but melts at 29.7°C.",
            "insight": "Gallium's low melting point and high boiling point make it useful in semiconductors. It also attacks aluminum's crystal structure, making it brittle.",
            "keywords": ["gallium", "melting point", "metal", "semiconductors"],
            "category": "chemistry_reactions",
        },
        # Technology & Future
        {
            "title": "Graphene: The Wonder Material We Can't Mass Produce",
            "hook": "One atom thick, 200x stronger than steel, conducts electricity better than copper.",
            "insight": "Isolated in 2004 with Scotch tape. The challenge isn't making it—it's making large, defect-free sheets affordably.",
            "keywords": ["graphene", "materials science", "nanotechnology", "future tech"],
            "category": "technology_future",
        },
        {
            "title": "Quantum Computers: Why They're Not Just Faster",
            "hook": "They don't just calculate faster—they calculate differently.",
            "insight": "Qubits use superposition and entanglement. They explore all paths simultaneously. Breaking RSA encryption would take a classical computer billions of years; a quantum computer: hours.",
            "keywords": ["quantum computing", "qubits", "superposition", "encryption", "computing"],
            "category": "technology_future",
        },
        # Human Body
        {
            "title": "Your Stomach Gets a New Lining Every 3-4 Days",
            "hook": "Stomach acid would digest your stomach if it didn't constantly regenerate.",
            "insight": "The mucus-bicarbonate barrier protects the lining. Cells divide rapidly to replace those destroyed by HCl and pepsin. Without this, you'd digest yourself.",
            "keywords": ["stomach lining", "regeneration", "digestion", "human biology"],
            "category": "human_body",
        },
        {
            "title": "You're Taller in the Morning Than at Night",
            "hook": "You shrink up to 2cm during the day.",
            "insight": "Spinal discs compress under gravity. Overnight, they rehydrate and expand. Astronauts grow 3-5cm taller in space.",
            "keywords": ["spine", "height", "gravity", "spinal discs", "astronauts"],
            "category": "human_body",
        },
        # Nature & Animals
        {
            "title": "The Pistol Shrimp Creates a Flash Hotter Than the Sun",
            "hook": "Its claw snaps shut so fast it creates a cavitation bubble reaching 4700°C.",
            "insight": "The collapsing bubble produces sonoluminescence—a flash of light. The shockwave stuns prey. It's one of the loudest animals in the ocean.",
            "keywords": ["pistol shrimp", "cavitation", "sonoluminescence", "marine biology"],
            "category": "nature_animals",
        },
        {
            "title": "The Mimic Octopus: Nature's Ultimate Impersonator",
            "hook": "It can impersonate 15+ different species—lionfish, flatfish, sea snakes.",
            "insight": "It changes color, texture, AND behavior. It chooses impersonations based on what predator is nearby. It's not just camouflage—it's acting.",
            "keywords": ["mimic octopus", "camouflage", "impersonation", "marine biology"],
            "category": "nature_animals",
        },
        # Ocean Mysteries
        {
            "title": "The Bloop: The Loudest Underwater Sound Ever Recorded",
            "hook": "In 1997, hydrophones picked up a sound heard 5000km away.",
            "insight": "Initially thought to be a massive unknown creature. Later identified as icequakes—massive icebergs cracking. But the mystery sparked giant sea monster theories.",
            "keywords": ["the bloop", "underwater sound", "hydrophones", "icequakes", "ocean mystery"],
            "category": "ocean_mysteries",
        },
        {
            "title": "Underwater Waterfalls: The Denmark Strait Cataract",
            "hook": "The world's largest waterfall is underwater, 3x taller than Angel Falls.",
            "insight": "Cold, dense water from the Nordic Seas plunges 3500m down the Denmark Strait. It's a critical driver of global ocean circulation.",
            "keywords": ["underwater waterfall", "denmark strait", "ocean circulation", "cataract"],
            "category": "ocean_mysteries",
        },
        # Quantum Weirdness
        {
            "title": "Quantum Tunneling: Particles Walking Through Walls",
            "hook": "Particles can appear on the other side of an impenetrable barrier.",
            "insight": "Wave-particle duality means there's a probability the particle exists on the other side. Without it, the Sun wouldn't shine—protons couldn't overcome repulsion to fuse.",
            "keywords": ["quantum tunneling", "quantum mechanics", "fusion", "sun", "physics"],
            "category": "quantum_weirdness",
        },
        {
            "title": "Schrödinger's Cat: The Paradox That Broke Physics",
            "hook": "A cat in a box is simultaneously dead and alive until observed.",
            "insight": "Schrödinger created this to SHOW the absurdity of quantum superposition at macroscopic scales. It wasn't a proposal—it was a critique. The measurement problem remains unsolved.",
            "keywords": ["schrodinger's cat", "quantum superposition", "measurement problem", "quantum mechanics"],
            "category": "quantum_weirdness",
        },
    ]

    def __init__(self, db_session):
        self.db = db_session

    def seed_topic_bank(self, channel_id: int) -> int:
        """Seed the topic bank with Science Curiosity topics."""
        count = 0
        for topic_data in self.SEED_TOPICS:
            # Check if already exists
            existing = (
                self.db.query(VideoTopic)
                .filter(
                    VideoTopic.channel_id == channel_id,
                    VideoTopic.title == topic_data["title"],
                )
                .first()
            )

            if existing:
                continue

            topic = VideoTopic(
                channel_id=channel_id,
                title=topic_data["title"],
                hook=topic_data["hook"],
                insight=topic_data["insight"],
                keywords=topic_data["keywords"],
                category=topic_data["category"],
                language="en",
                score=75,  # Base score for curated topics
                priority=50,
                status=VideoTopicStatus.ACTIVE,
            )
            self.db.add(topic)
            count += 1

        # Also add the category topics as generic templates
        for category in self.CATEGORIES:
            existing = (
                self.db.query(VideoTopic)
                .filter(
                    VideoTopic.channel_id == channel_id,
                    VideoTopic.category == category,
                    VideoTopic.title.like(f"%{category}%"),
                )
                .first()
            )

            if not existing:
                topic = VideoTopic(
                    channel_id=channel_id,
                    title=f"Amazing {category.replace('_', ' ').title()} Facts",
                    hook=f"Mind-blowing facts about {category.replace('_', ' ')} that will change how you see the world.",
                    insight="Curated collection of the most fascinating discoveries in this field.",
                    keywords=[category.replace("_", " "), "facts", "science", "education"],
                    category=category,
                    language="en",
                    score=60,
                    priority=30,
                    status=VideoTopicStatus.ACTIVE,
                )
                self.db.add(topic)
                count += 1

        return count

    def get_topics_by_category(self, channel_id: int, category: str) -> list[VideoTopic]:
        """Get all active topics in a category."""
        return (
            self.db.query(VideoTopic)
            .filter(
                VideoTopic.channel_id == channel_id,
                VideoTopic.category == category,
                VideoTopic.status == VideoTopicStatus.ACTIVE,
            )
            .order_by(VideoTopic.score.desc())
            .all()
        )

    def re_score_topic(self, topic_id: int, new_score: int) -> bool:
        """Update topic score based on performance feedback."""
        topic = self.db.query(VideoTopic).get(topic_id)
        if not topic:
            return False
        topic.score = max(0, min(100, new_score))
        return True

    def get_exhausted_topics(self, channel_id: int) -> list[VideoTopic]:
        """Get topics that have been used 3+ times."""
        return (
            self.db.query(VideoTopic)
            .filter(
                VideoTopic.channel_id == channel_id,
                VideoTopic.status == VideoTopicStatus.EXHAUSTED,
            )
            .all()
        )

    def reset_exhausted_topics(self, channel_id: int) -> int:
        """Reset exhausted topics back to active (for long-running channels)."""
        topics = self.get_exhausted_topics(channel_id)
        for topic in topics:
            topic.status = VideoTopicStatus.ACTIVE
            topic.usage_count = 0
        return len(topics)
