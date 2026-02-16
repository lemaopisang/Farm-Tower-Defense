"""Farm Tower Defense - Python Edition.

This module contains a console-based, turn-based combat game inspired by the
original Dart implementation. The code has been refactored to provide a cleaner
architecture that is easier to test and extend.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence


KONAMI_SEQUENCE: Sequence[str] = (
    "up",
    "up",
    "down",
    "down",
    "left",
    "right",
    "left",
    "right",
    "b",
    "a",
)

STORY_END_WAVE = 25

RANDOM_EVENTS: Sequence[str] = (
    "Mysterious Merchant",
    "Lightning Storm",
    "Lost Cow Returns",
    "Strange Seed Sprouts",
    "A Trap",
    "Wandering Bard",
    "Locust Swarm",
    "Irrigation Boom",
    "Moonlit Harvest",
)

BAD_EVENTS: Sequence[str] = (
    "Sudden Hail",
    "Rusty Pitchfork",
    "Thorny Brambles",
)

BOSS_TITLES: dict[int, str] = {
    5: "Gorecrow",
    10: "Scorch Herald",
    15: "Rusthorn",
    20: "Emberlord",
    25: "Gravelox",
}

BOSS_ASCII: dict[int, str] = {
    5: "  .-^-.\n (o o)\n  |=|  Scarecrow\n /___\\",
    10: "  /\\\\\n (🔥 )  Scorch\n  \\//",
    15: "  /\\_/\\\n ( o.o )  Rusthorn\n  > ^ <",
    20: "  .-^^-.\n (🔥🔥)  Emberlord\n  ||||",
    25: "  /\\__/\\\n ( o_o )  Gravelox\n /  _  \\",
}

AREA_RANGES: Sequence[tuple[int, int, str, str]] = (
    (1, 10, "Meadowfront", "Soft grass, warm wind, and a distant scarecrow.") ,
    (11, 20, "Ashen Fields", "The soil is warm to the touch, embers float in the air."),
    (21, 30, "Ironridge", "Rocky furrows and clanging windmills grind the horizon."),
    (31, 9999, "Endless Verge", "The land stretches forever, hungry for another wave."),
)

WAVE_RANGE_EVENTS: Sequence[tuple[range, Sequence[str]]] = (
    (range(1, 11), ("Butterfly Bloom", "Soggy Furrows")),
    (range(11, 21), ("Cinder Drift", "Charred Fence")),
    (range(21, 31), ("Gravel Gust", "Rusted Plow")),
)


class IOInterface:
    """Abstract IO layer so the game can be tested without a console."""

    def write(self, text: str) -> None:
        raise NotImplementedError

    def prompt(self, text: str) -> str:
        raise NotImplementedError


class ConsoleIO(IOInterface):
    """Default IO implementation that uses the Python console."""

    def write(self, text: str) -> None:
        print(text)

    def prompt(self, text: str) -> str:
        return input(text)


class KonamiManager:
    """Tracks Konami code input and applies related game bonuses."""

    def __init__(self, sequence: Sequence[str], rng: random.Random, max_uses: int = 0) -> None:
        self.sequence = list(sequence)
        self.buffer: List[str] = []
        self.rng = rng
        self.max_uses = max_uses
        self.uses = 0
        self.locked = False
        self.hints = (
            "A strange breeze whistles... like a whisper of old codes.",
            "You feel your fingers itching for a rhythm you've never learned.",
            "The soil pulses with hidden power. What if you... remembered something forgotten?",
            "A distant memory nudges your thoughts—up, up, down...?",
        )

    def push(self, value: str) -> bool:
        value = value.lower().strip()
        if not value:
            return False

        self.buffer.append(value)
        if len(self.buffer) > len(self.sequence):
            self.buffer.pop(0)

        unlimited = self.max_uses <= 0
        if self.buffer == self.sequence and not self.locked and (unlimited or self.uses < self.max_uses):
            self.buffer.clear()
            self.uses += 1
            if not unlimited and self.uses >= self.max_uses:
                self.locked = True
            return True

        if self.buffer != self.sequence[: len(self.buffer)] and self.rng.random() < 0.15:
            # Provide a gentle hint when the sequence does not match.
            raise KonamiHint(self.rng.choice(self.hints))

        return False

    def check_sequence(self, inputs: Iterable[str]) -> bool:
        """Check a full sequence (used when activating a purchased fragment).

        This method compares the provided inputs to the Konami sequence exactly
        (case-insensitive). If it matches and uses remain, it consumes one use
        and returns True. Otherwise returns False.
        """
        # normalize
        tokens = [str(x).lower().strip() for x in inputs]
        unlimited = self.max_uses <= 0
        if tokens == self.sequence and not self.locked and (unlimited or self.uses < self.max_uses):
            self.uses += 1
            if not unlimited and self.uses >= self.max_uses:
                self.locked = True
            return True
        return False

    def unlocks_remaining(self) -> int:
        if self.max_uses <= 0:
            return 999999
        return max(0, self.max_uses - self.uses)


class KonamiHint(RuntimeError):
    """Internal exception to signal that a hint should be shown to the player."""


class Farm:
    """Base class shared by the player farm and enemies."""

    def __init__(self, name: str, health: int, attack_power: int) -> None:
        self.name = name
        self.max_hp = health
        self.health = health
        self.attack_power = attack_power

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def display_hp(self) -> str:
        return f"{self.health}/{self.max_hp}"

    def heal_percent(self, percent: float) -> int:
        amount = round(self.max_hp * percent)
        self.health = min(self.max_hp, self.health + amount)
        return amount

    def damage_percent(self, percent: float) -> int:
        amount = round(self.max_hp * percent)
        self.health = max(0, self.health - amount)
        return amount

    def heal_flat(self, amount: int) -> int:
        self.health = min(self.max_hp, self.health + amount)
        return amount

    def take_damage(self, amount: int) -> int:
        self.health = max(0, self.health - amount)
        return amount

    def roll_attack_damage(self, rng: random.Random) -> int:
        multiplier = rng.uniform(0.8, 1.2)
        return round(multiplier * self.attack_power)

    def apply_attack_damage(self, other: "Farm", damage: int) -> int:
        other.take_damage(damage)
        return damage

    def attack(self, other: "Farm", rng: random.Random) -> int:
        damage = self.roll_attack_damage(rng)
        return self.apply_attack_damage(other, damage)


@dataclass
class Skill:
    name: str
    description: str
    effect: Callable[["PlayerFarm", Farm, IOInterface], None]
    cooldown: int = 0

    def use(self, player: "PlayerFarm", target: Farm, io: IOInterface) -> None:
        self.effect(player, target, io)



class PlayerFarm(Farm):
    def __init__(self, name: str) -> None:
        super().__init__(name=name, health=150, attack_power=25)
        self.skills: List[Skill] = []
        self.coins: int = 0
        self.gold: int = 0
        self.rng = random.Random()
        # temporary tonic protection
        self.tonic_turns: int = 0
        self.tonic_reduction: float = 0.0
        # skill_name -> remaining cooldown turns
        self.skill_cooldowns: dict[str, int] = {}
        # passive effects from bosses: name -> (stacks, stackable)
        self.passives: dict[str, tuple[int, bool]] = {}
        # konami fragments dropped by bosses (guaranteed), capped at 3
        self.konami_fragments: int = 0
        self.konami_fragment_rounds_left: int = 0
        self.konami_purchase_count: int = 0
        self.gold_tip_shown: bool = False
        self.merchant_skill_given: bool = False
        self.temp_attack_bonus: int = 0
        self.irrigation_attack_turns: int = 0
        self.irrigation_attack_bonus: float = 0.0
        self.irrigation_shield: int = 0

    def take_damage(self, amount: int) -> int:
        if self.irrigation_shield > 0 and amount > 0:
            absorbed = min(amount, self.irrigation_shield)
            self.irrigation_shield -= absorbed
            amount -= absorbed
        return super().take_damage(amount)

    def attack(self, other: "Farm", rng: random.Random) -> int:
        damage = self.roll_attack_damage(rng)
        if self.irrigation_attack_turns > 0 and self.irrigation_attack_bonus > 0:
            damage = round(damage * (1 + self.irrigation_attack_bonus))
            self.irrigation_attack_turns -= 1
            if self.irrigation_attack_turns <= 0:
                self.irrigation_attack_bonus = 0.0
        return self.apply_attack_damage(other, damage)

    def wave_clear_upgrade(self) -> None:
        self.attack_power += 5
        self.max_hp += 10
        self.health = self.max_hp

    def add_new_skill(self, io: Optional[IOInterface] = None) -> None:
        available = list(self._all_skills())
        # randomize available skills and pick a new one if any
        self.rng = getattr(self, 'rng', random.Random())
        self.rng.shuffle(available)
        for skill in available:
            if all(existing.name != skill.name for existing in self.skills):
                self.skills.append(skill)
                if io:
                    io.write(f"✨ New skill acquired: {skill.name}!")
                return
        if io:
            io.write("No new skill found. All unlocked.")

    def attack_boost(self) -> None:
        self.attack_power += 20

    def defense_boost(self) -> None:
        self.max_hp += 50
        self.health = min(self.max_hp, self.health)

    def konami_activation_cost(self, extra_tiers: int = 0) -> tuple[int, int]:
        tiers = (self.konami_purchase_count // 3) + max(0, extra_tiers)
        coins = 7 + (tiers * 2)
        gold = 5 + tiers
        return coins, gold

    def _all_skills(self) -> Iterable[Skill]:
        # Reworked skill set: more variety, cooldowns, and attack-power based scaling
        return (
            Skill(
                "Blazing Corn",
                "Deal 30% of enemy current HP + 30% of your attack power and stun the enemy.",
                lambda p, e, io: self._skill_blazing_corn(p, e, io),
                cooldown=4,
            ),
            Skill(
                "Rain Dance",
                "Restore HP equal to 30% of your max HP + 50% of your attack power.",
                lambda p, e, io: self._skill_rain_dance_buffed(p, io),
                cooldown=5,
            ),
            Skill(
                "Stampede",
                "Strike for 1.3x attack power, reduce enemy next attack, and you take 30% recoil.",
                lambda p, e, io: self._skill_stampede_buffed(p, e, io),
                cooldown=5,
            ),
            Skill(
                "Fortify Fence",
                "Permanently increase max HP by 25.",
                lambda p, e, io: self._skill_increase_max_hp(p, 25, io),
                cooldown=9999,  # passive/once-use ultimate-style
            ),
            Skill(
                "Sap Burst",
                "Deal 0.9x attack power and heal for 12% of your max HP.",
                lambda p, e, io: self._skill_sap_burst(p, e, io),
                cooldown=3,
            ),
            Skill(
                "Concussive Seed",
                "Deal 0.5x attack power and stun the enemy to skip its next turn.",
                lambda p, e, io: self._skill_concussive_seed(p, e, io),
                cooldown=4,
            ),
        )

    @staticmethod
    def _skill_increase_max_hp(player: "PlayerFarm", amount: int, io: IOInterface) -> None:
        player.max_hp += amount
        player.health += amount
        io.write(f"🛡️ Fortify Fence raises Farm's max HP by {amount}.")


    @staticmethod
    def _skill_blazing_corn(player: "PlayerFarm", enemy: Farm, io: IOInterface) -> None:
        damage = round(enemy.health * 0.3) + round(player.attack_power * 0.3)
        enemy.take_damage(damage)
        setattr(enemy, 'stunned', True)
        io.write(f"🔥 Blazing Corn deals {damage} damage and stuns {enemy.name} (they skip their next turn)!")

    @staticmethod
    def _skill_rain_dance_buffed(player: "PlayerFarm", io: IOInterface) -> None:
        amount = round(player.max_hp * 0.3) + round(player.attack_power * 0.5)
        player.heal_flat(amount)
        io.write(f"🌧️ Rain Dance restores {amount} HP!")

    @staticmethod
    def _skill_stampede(player: "PlayerFarm", enemy: Farm, io: IOInterface) -> None:
        damage = round(player.attack_power * 1.3)
        enemy.take_damage(damage)
        # apply a debuff: reduce enemy attack this turn by 30%
        if hasattr(enemy, 'attack_debuff'):
            enemy.attack_debuff += 0.3
        else:
            setattr(enemy, 'attack_debuff', 0.3)
        # recoil 30% of damage dealt
        recoil = round(damage * 0.3)
        player.take_damage(recoil)
        io.write(f"🐄 Stampede hits {enemy.name} for {damage} damage, you recoil {recoil} HP and reduce their next attack!")

    def _skill_stampede_buffed(self, player: "PlayerFarm", enemy: Farm, io: IOInterface) -> None:
        return PlayerFarm._skill_stampede(player, enemy, io)

    @staticmethod
    def _skill_concussive_seed(player: "PlayerFarm", enemy: Farm, io: IOInterface) -> None:
        damage = round(player.attack_power * 0.5)
        enemy.take_damage(damage)
        # apply stun flag for one turn
        setattr(enemy, 'stunned', True)
        io.write(f"🌱 Concussive Seed hits for {damage} and stuns {enemy.name}!")

    @staticmethod
    def _skill_sap_burst(player: "PlayerFarm", enemy: Farm, io: IOInterface) -> None:
        damage = round(player.attack_power * 0.9)
        enemy.take_damage(damage)
        heal = player.heal_percent(0.12)
        io.write(f"🌿 Sap Burst deals {damage} damage and restores {heal} HP.")


class Monster(Farm):
    def __init__(self, wave: int) -> None:
        super().__init__(
            name="Enemy Monster",
            # buffed base stats
            health=100 + int(wave * 12),
            attack_power=12 + int(wave * 3),
        )


class Boss(Monster):
    def __init__(self, wave: int) -> None:
        super().__init__(wave)
        title = BOSS_TITLES.get(wave)
        if title:
            self.name = f"{title} (Wave {wave})"
        else:
            self.name = f"Endless Warden (Wave {wave})"
        # scale boss strength depending on progression so early bosses aren't crushing
        if wave <= 10:
            add_hp = 80
            add_attack = 15
        elif wave <= 30:
            add_hp = 150
            add_attack = 30
        else:
            add_hp = 250
            add_attack = 40
        self.max_hp += add_hp
        self.health += add_hp
        self.attack_power += add_attack
        # boss gives a passive option when defeated
        self.passive_reward = (
            "Ember's Fury",
            "Gain +5 attack per stack (stackable up to 3 times).",
            True,
        )

class Game:
    def __init__(
        self,
        io: Optional[IOInterface] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.io = io or ConsoleIO()
        self.rng = rng or random.Random()
        self.wave = 1
        self.konami_manager = KonamiManager(KONAMI_SEQUENCE, rng=self.rng)
        self.used_events: set[str] = set()
        self.player: Optional[PlayerFarm] = None
        self.turn_count = 0
        self.endless_mode = False
        self.current_area: Optional[str] = None
        self.stop_requested = False

    def start(self) -> None:
        self.io.write("Oh hey, welcome to this Game thing that I made. ")
        input("[Press Enter to continue the yapping]")
        self.io.write("This game was actually going to be Dart-based(yes crazy I know).")
        self.io.write("But it ends up being like this, a Python-based text CLI game.")
        input("[Press Enter to continue the yapping]")
        self.io.write("But hey, at least you played this version!")
        input("[Press Enter to continue the yapping]")
        self.io.write("Feel free to play this game in your own will, or not.")
        self.io.write("If you're an Anti-AI, then just hop off.")
        input("[Press Enter to continue the yapping]")
        self.io.write("Or if you don't really care all that shit, it's up to you.")
        input("[Press Enter to finish yapping]")
        self.io.write("Have fun. | Creator's Note 1")
        input("[Press Enter to finally finished yapping]")
        while True:
            self.io.write("\n=== Main Menu ===")
            self.io.write("1) Start")
            self.io.write("2) Creator's notes")
            self.io.write("3) Update notes")
            choice = (self.io.prompt("Choose an option: ") or "").strip().lower()
            if choice in {"1", "start", "s"}:
                break
            if choice in {"2", "creator", "creator's notes", "notes", "c"}:
                self.io.write("\nCreator's Notes:")
                self.io.write("Oh hey, welcome to this Game thing that I made. ")
                input("[Press Enter to continue the yapping]")
                self.io.write("This game was actually going to be Dart-based(yes crazy I know).")
                self.io.write("But it ends up being like this, a Python-based text CLI game.")
                input("[Press Enter to continue the yapping]")
                self.io.write("But hey, at least you played this version!")
                input("[Press Enter to continue the yapping]")
                self.io.write("Feel free to play this game in your own will, or not.")
                self.io.write("If you're an Anti-AI, then just hop off.")
                input("[Press Enter to continue the yapping]")
                self.io.write("Or if you don't really care all that shit, it's up to you.")
                input("[Press Enter to finish yapping]")
                self.io.write("Have fun. | Creator's Note 1")
                input("[Press Enter to finally finished yapping]")
                continue
            if choice in {"3", "update", "updates", "u"}:
                self.io.write("\nUpdate Notes: V0.10 | Alpha")
                self.io.write("- Added a main menu with Start, Creator's Notes, and Update Notes.")
                self.io.write("- Preserved the full intro/yapping section cuz y not?")
                self.io.write("- Expanded random events and made 'another random event'")
                self.io.write("- Added area transitions and story flavor between waves")
                self.io.write("- Added Endless Mode, more info when passing Wave 30")
                self.io.write("- Shop now includes more upgrades with clearer pricing/limits.")
                self.io.write("- Konami fragments last 5 rounds if unused; activations are unlimited.")
                self.io.write("- Boss haves names and ASCII art when they appeared!!")
                self.io.write("- Fixed damage reduction and Temporary Buff")
                self.io.write("- Rebalance Endless mode scaling on further waves")
                self.io.write("- Endless enemies now gets rid of ur HP based on your max HP.")
                self.io.write("- Lost Cow now shows the shield amount scaled by 3× max HP, y not?")
                self.io.write("- Strange Seed and Konami activations now spit out the buff numbers.")
                input("[Press Enter to go back.]")
                continue
            input("Just pick anything bro dont mess this one up🥀")
        self.io.write("You might want to extend your terminal a bit if you're playing with one.")
        name = self.io.prompt("Enter your Farm name: ") or "Farm"
        self.player = PlayerFarm(name)
        # give the player a starting coin so shop is useful
        self.player.coins = 2

        try:
            while self.player.is_alive and not self.stop_requested:
                self._play_wave()
                if self.stop_requested:
                    break
                if not self.player.is_alive:
                    break
                self.player.wave_clear_upgrade()
                self.wave += 1
        except KeyboardInterrupt:
            self.io.write("\n👋 Thanks for playing! Try again if you want.")
            return

        if self.stop_requested and self.player.is_alive:
            self.io.write(f"\n🌾 {self.player.name} retires after wave {self.wave}. Thanks for playing!")
        else:
            self.io.write(f"\n💀 {self.player.name} has fallen at wave {self.wave}.")
            self.io.write("🌾 Thanks for playing!")

    def _play_wave(self) -> None:
        assert self.player is not None
        if not self.endless_mode and self.wave > STORY_END_WAVE:
            if not self._prompt_endless_mode():
                self.stop_requested = True
                return
            self.endless_mode = True
            self.io.write("\n🌌 Endless mode begins! Hope that you don't get bored.")
        self._enter_area_if_needed()
        enemy = Boss(self.wave) if self.wave % 5 == 0 else Monster(self.wave)
        if self.endless_mode:
            extra = max(0, self.wave - STORY_END_WAVE)
            if isinstance(enemy, Boss):
                enemy.max_hp += extra * 30
                enemy.health += extra * 30
                enemy.attack_power += extra * 6
            else:
                enemy.max_hp += extra * 20
                enemy.health += extra * 20
                enemy.attack_power += extra * 4
        self.io.write(f"\n=== Wave {self.wave} ===")
        self._story_arc(self.wave)
        if isinstance(enemy, Boss):
            art = BOSS_ASCII.get(self.wave)
            if art:
                for line in art.splitlines():
                    self.io.write(line)
        # shop every 2 waves
        if self.wave % 2 == 0:
            self._open_shop()
        # Konami fragments corrode after 5 rounds
        if self.player.konami_fragments > 0:
            self.player.konami_fragment_rounds_left -= 1
            if self.player.konami_fragment_rounds_left <= 0:
                self.player.konami_fragments = 0
                self.player.konami_fragment_rounds_left = 0
                self.io.write("Your fragment disappeared.")
        # ensure temporary buffs from shop only last for this wave
        self._battle(enemy)
        if self.player.temp_attack_bonus > 0:
            self.player.attack_power = max(0, self.player.attack_power - self.player.temp_attack_bonus)
            self.player.temp_attack_bonus = 0

    def _battle(self, enemy: Farm) -> None:
        assert self.player is not None
        # battle loop with cooldown ticking and turn limits
        self.turn_count = 0
        long_battle_threshold = 10
        boss_threshold = 15
        while self.player.is_alive and enemy.is_alive:
            self.turn_count += 1
            # increase enemy scaling if battle goes too long
            if self.turn_count >= long_battle_threshold and not isinstance(enemy, Boss):
                # scale by 1.5x
                enemy.attack_power = int(enemy.attack_power * 1.5)
                self.io.write(f"⚠️ The enemy is getting Stronger by the turn!")
            if self.turn_count >= boss_threshold and isinstance(enemy, Boss):
                enemy.attack_power = int(enemy.attack_power * 1.5)
                self.io.write(f"⚠️ The boss's getting impatient, it gets Stronger!")

            # show status
            self.io.write(
                f"\n{self.player.name}: {self.player.display_hp()} | "
                f"{enemy.name}: {enemy.display_hp()} | Coins: {self.player.coins}"
            )

            # tick down cooldowns
            for k in list(self.player.skill_cooldowns.keys()):
                if self.player.skill_cooldowns[k] > 0:
                    self.player.skill_cooldowns[k] -= 1
                    if self.player.skill_cooldowns[k] == 0:
                        del self.player.skill_cooldowns[k]

            # in-battle actions
            self._show_options(enemy)

            if self.endless_mode and enemy.is_alive:
                self._maybe_trigger_endless_gimmick(enemy)

            # enemy action
            if enemy.is_alive:
                # handle stun
                if getattr(enemy, 'stunned', False):
                    self.io.write(f"{enemy.name} got stunned and can't act this turn!")
                    delattr(enemy, 'stunned')
                else:
                    # apply any attack debuff
                    debuff = getattr(enemy, 'attack_debuff', 0)
                    base = enemy.roll_attack_damage(self.rng)
                    actual = max(0, int(base * (1 - debuff))) if debuff else base
                    if debuff:
                        # reset debuff after used
                        enemy.attack_debuff = 0
                    # apply player tonic reduction if active
                    if self.player.tonic_turns > 0 and self.player.tonic_reduction > 0:
                        reduced = int(actual * (1 - self.player.tonic_reduction))
                        self.io.write(f"Your tonic reduce your Damage taken from {actual} to {reduced} this turn.")
                        actual = reduced
                        self.player.tonic_turns -= 1
                        if self.player.tonic_turns == 0:
                            self.player.tonic_reduction = 0.0
                    self.player.take_damage(actual)
                    self.io.write(f"{enemy.name} attacks {self.player.name} for {actual} damage!")

            # check death to award coins
            if not enemy.is_alive:
                reward = 6 if not isinstance(enemy, Boss) else 15
                self.player.coins += reward
                self.io.write(f"🎉 You defeated {enemy.name}! Coins +{reward} (Total: {self.player.coins})")
                # Boss gives passive choice
                if isinstance(enemy, Boss):
                    # guaranteed konami fragment drop if player has less than 3
                    if self.player.konami_fragments < 3:
                        self.player.konami_fragments += 1
                        self.player.konami_fragment_rounds_left = 5
                        self.io.write("Konami Fragment Obtained from the Boss!")
                    self._offer_boss_passive(enemy)

    def _show_options(self, enemy: Farm) -> None:
        assert self.player is not None
        self.io.write("Choose action: [1] Attack  [2] Heal  [3] Skill")
        choice = self.io.prompt("> ").strip()

        if choice == "1":
            damage = self.player.attack(enemy, self.rng)
            self.io.write(f"{self.player.name} attacks {enemy.name} for {damage} damage!")
        elif choice == "2":
            amount = self.player.heal_flat(50)
            self.io.write(f"{self.player.name} uses a heal and recovers {amount} HP.")
        elif choice == "3":
            self._handle_skill(enemy)
        else:
            # fail dialogue for invalid action
            self.io.write("Enemy gets a free turn due to your no focus, lol.")

    def _handle_skill(self, enemy: Farm) -> None:
        assert self.player is not None

        if not self.player.skills:
            self.io.write("You have no skills yet, so you just emoted lolz")
            return

        self.io.write("Available Skills:")
        for idx, skill in enumerate(self.player.skills, start=1):
            cd = self.player.skill_cooldowns.get(skill.name, 0)
            cd_text = f" (CD: {cd})" if cd else ""
            self.io.write(f"{idx}. {skill.name} — {skill.description}{cd_text}")

        try:
            index_raw = self.io.prompt("Choose a skill: ").strip()
            index = int(index_raw) - 1
        except ValueError:
            self.io.write("Meh, that skill doesn't exist, so you emoted lolz")
            return

        if 0 <= index < len(self.player.skills):
            skill = self.player.skills[index]
            # check cooldown
            if skill.name in self.player.skill_cooldowns and self.player.skill_cooldowns[skill.name] > 0:
                self.io.write(f"{skill.name} is on cd for {self.player.skill_cooldowns[skill.name]} more turns.")
                self.io.write("Be patience, jeez.")
                return
            # use skill
            skill.use(self.player, enemy, self.io)
            # set cooldown if present
            if getattr(skill, 'cooldown', 0):
                cd = int(getattr(skill, 'cooldown', 0))
                if cd > 0 and cd < 9999:
                    self.player.skill_cooldowns[skill.name] = cd
        else:
            self.io.write("Meh, that skill doesn't exist, so you emoted lolz")

    def _offer_boss_passive(self, boss: Boss) -> None:
        assert self.player is not None
        # boss.passive_reward: (name, desc, stackable)
        try:
            name, desc, stackable = boss.passive_reward
        except Exception:
            return
        stacks, _ = self.player.passives.get(name, (0, stackable))
        initial_stacks = stacks
        if stacks >= 3:
            return
        # Auto-apply passive. Small chance for an extra stack, tiny chance for backlash.
        self.io.write(f"\n🏆 Boss Reward: {name} — {desc} Obtained!")
        stacks = min(3, stacks + 1)
        self.player.passives[name] = (stacks, stackable)
        if name == "Ember's Fury":
            self.player.attack_power += 5
        # 20% chance to immediately grant +1 extra stack if available (but not on first acquisition)
        if stackable and initial_stacks > 0 and stacks < 3 and self.rng.random() < 0.2:
            stacks = min(3, stacks + 1)
            self.player.passives[name] = (stacks, stackable)
            if name == "Ember's Fury":
                self.player.attack_power += 5
            self.io.write("A surge amplifies the reward! An extra stack is granted.")
        # 10% chance small backlash
        if self.rng.random() < 0.10:
            lost = max(1, int(self.player.max_hp * 0.05))
            self.player.take_damage(lost)
            self.io.write(f"The passive leaves a bitter aftertaste. You lose {lost} HP.")
        self.io.write(f"Passive applied. Current stacks: {stacks}.")

    def _story_arc(self, wave: int) -> None:
        assert self.player is not None
        if wave % 5 == 0:
            self.io.write(f"\n📜 STORY ARC [{wave}]")
            if wave == 5:
                self.io.write("A shadow farmer raids your field. Something darker looms...")
            elif wave == 10:
                self.io.write("A cult called Scorch appears — burning farms across the land.")
            elif wave == 15:
                self.io.write("A rogue survivor teaches you a mysterious skill, before the boss came.")
                self.player.add_new_skill(self.io)
            elif wave == 20:
                self.io.write("The Emberlord arrives, flames rise around your barn.")
            elif wave == 25:
                self.io.write("You uncover the truth. Will you DEFEND [1] or STRIKE BACK [2]?")
                decision = self.io.prompt("> ").strip()
                if decision == "1":
                    self.player.defensive_path = True
                    self.io.write("You fortify your land. Defense increased!")
                    self.player.defense_boost()
                else:
                    self.io.write("You prepare to counterattack! Attack increased!")
                    self.player.attack_boost()

        # Trigger random events on every 3rd wave, except at specific story marks
        if wave > 1 and wave % 3 == 0:
            if wave in (5, 10, 15):
                return
            self._trigger_random_event()

    def _enter_area_if_needed(self) -> None:
        for start, end, name, detail in AREA_RANGES:
            if start <= self.wave <= end:
                if self.current_area != name:
                    self.current_area = name
                    self.io.write(f"\n🗺️ Area: {name}")
                    self.io.write(detail)
                    _ = self.io.prompt("Press Enter to continue...")
                return

    def _prompt_endless_mode(self) -> bool:
        self.io.write("\n📣 Story complete. Endless Mode is available!")
        self.io.write("Changes ahead:")
        self.io.write("- Enemies scale harder every wave.")
        self.io.write("- Shop items upgrade to end-game versions.")
        self.io.write("- Random events expand and can chain.")
        self.io.write("- Endless foes now siphon a sliver of your max HP each turn.")
        self.io.write("Choose to continue or completely stop.")
        answer = (self.io.prompt("Enter Endless Mode? (y/n): ") or "n").strip().lower()
        return answer in ("y", "yes")

    def _open_shop(self) -> None:
        assert self.player is not None
        # loop shop until the player chooses to leave
        while True:
            extra_tiers = 1 if self.endless_mode else 0
            coins_cost, gold_cost = self.player.konami_activation_cost(extra_tiers)
            self.io.write("\n🏪 The traveling shop appears! You may buy items:")
            if self.endless_mode:
                self.io.write("[1] Ironbark Brew (10 coins) - reduce incoming damage by 45% for 2 turns")
                self.io.write("[2] War Banner (12 coins) - +20 attack for this wave")
                self.io.write("[3] Golden Relic (15 coins) - gain 2 gold")
                self.io.write("[4] Ancient Seed (2 gold) - permanently +8 attack and +20 max HP")
            else:
                self.io.write("[1] Field Tonic (8 coins) - reduce incoming damage by 30% for 3 turns")
                self.io.write("[2] Attack Tonic (6 coins) - +12 attack for this wave")
                self.io.write("[3] Gold Pouch (pay 10 coins) - gain 1 gold")
                self.io.write("[4] Blessed Seed (1 gold) - permanently +3 attack and +10 max HP")
            self.io.write(f"[5] Activate Konami Fragment ({gold_cost} gold + {coins_cost} coins)")
            self.io.write("[6] Leave")
            choice = self.io.prompt("> ").strip()
            if choice == "1":
                if self.player.tonic_turns > 0:
                    self.io.write("This item is still in effect, buy a different one.")
                else:
                    if self.endless_mode:
                        if self.player.coins >= 10:
                            self.player.coins -= 10
                            self.player.tonic_turns = 2
                            self.player.tonic_reduction = 0.45
                            self.io.write("You drink an Ironbark Brew. Damage reduced by 45% for 2 turns.")
                        else:
                            self.io.write("Not enough coins.")
                    else:
                        if self.player.coins >= 8:
                            self.player.coins -= 8
                            self.player.tonic_turns = 3
                            self.player.tonic_reduction = 0.30
                            self.io.write("You apply a Field Tonic, reducing incoming damage by 30% for 3 turns.")
                        else:
                            self.io.write("Not enough coins.")
                    self.io.write(f"Coins: {self.player.coins} | Gold: {self.player.gold}")
            elif choice == "2":
                cost = 12 if self.endless_mode else 6
                buff = 20 if self.endless_mode else 12
                if self.player.coins >= cost:
                    self.player.coins -= cost
                    self.player.attack_power += buff
                    self.player.temp_attack_bonus += buff
                    if self.endless_mode:
                        self.io.write(f"You raise a War Banner in spirit. Attack +{buff} for this wave.")
                    else:
                        self.io.write(f"You drink the Attack Tonic. Attack +{buff} for this wave.")
                    self.io.write(f"Coins: {self.player.coins} | Gold: {self.player.gold}")
                else:
                    self.io.write("Not enough coins.")
            elif choice == "3":
                if self.endless_mode:
                    if self.player.coins >= 15:
                        self.player.coins -= 15
                        self.player.gold += 2
                        self.io.write("You purchase a Golden Relic and gain 2 gold.")
                        self.io.write(f"Coins: {self.player.coins} | Gold: {self.player.gold}")
                    else:
                        self.io.write("Not enough coins.")
                else:
                    if self.player.coins >= 10:
                        self.player.coins -= 10
                        self.player.gold += 1
                        self.io.write("You purchase a Gold Pouch and gain 1 gold.")
                        self.io.write(f"Coins: {self.player.coins} | Gold: {self.player.gold}")
                    else:
                        self.io.write("Not enough coins.")
            elif choice == "4":
                if self.endless_mode:
                    if self.player.gold >= 2:
                        self.player.gold -= 2
                        self.player.attack_power += 8
                        self.player.max_hp += 20
                        self.player.health = min(self.player.health + 20, self.player.max_hp)
                        self.io.write("You plant an Ancient Seed. Attack and Max HP surge permanently.")
                        self.io.write(f"Coins: {self.player.coins} | Gold: {self.player.gold}")
                    else:
                        self.io.write("Not enough gold.")
                        if not self.player.gold_tip_shown:
                            self.io.write("Tip: Buy a Gold Pouch with coins to get gold.")
                            self.player.gold_tip_shown = True
                else:
                    # spend gold for a Blessed Seed
                    if self.player.gold >= 1:
                        self.player.gold -= 1
                        self.player.attack_power += 3
                        self.player.max_hp += 10
                        self.player.health = min(self.player.health + 10, self.player.max_hp)
                        self.io.write("You plant the Blessed Seed. Attack and Max HP permanently increased.")
                        self.io.write(f"Coins: {self.player.coins} | Gold: {self.player.gold}")
                    else:
                        self.io.write("Not enough gold.")
                        if not self.player.gold_tip_shown:
                            self.io.write("Tip: Buy a Gold Pouch with coins to get gold.")
                            self.player.gold_tip_shown = True
            elif choice == "5":
                if self.player.konami_fragments > 0:
                    # require gold + coins to attempt activation
                    if self.player.gold < gold_cost or self.player.coins < coins_cost:
                        self.io.write(f"Activating a fragment costs {gold_cost} gold and {coins_cost} coins. You don't have enough resources.")
                        if not self.player.gold_tip_shown:
                            self.io.write("Tip: Buy a Gold Pouch with coins to get gold.")
                            self.player.gold_tip_shown = True
                    else:
                        self.io.write("Enter the Konami sequence tokens separated by spaces (e.g. 'up up down ...'):")
                        seq = self.io.prompt("> ").strip()
                        tokens = seq.split()
                        if self.konami_manager.check_sequence(tokens):
                            # consume fragment
                            self.player.konami_fragments -= 1
                            self.player.gold -= gold_cost
                            self.player.coins -= coins_cost
                            self.player.konami_purchase_count += 1
                            self.io.write("The Konami Fragment glows and releases power into you & your farm!")
                            # smaller buff: +30% of stats but in flat increases
                            atk_buff = max(1, int(self.player.attack_power * 0.3))
                            hp_buff = max(1, int(self.player.max_hp * 0.3))
                            self.player.attack_power += atk_buff
                            self.player.max_hp += hp_buff
                            self.player.health += hp_buff
                            self.player.add_new_skill(self.io)
                            self.io.write(f"Stats surge: Attack +{atk_buff}, Max HP +{hp_buff} (health +{hp_buff}).")
                            self.io.write(f"Coins: {self.player.coins} | Gold: {self.player.gold}")
                        else:
                            self.io.write("The sequence fizzles. The fragment resists activation.")
                            # failed activations have a small chance to break the fragment
                            if self.rng.random() < 0.25:
                                self.player.konami_fragments = max(0, self.player.konami_fragments - 1)
                                self.io.write("Your fragment breaks, due to failed attempt.")
                else:
                    self.io.write("You don't have one.")
            elif choice == "6":
                self.io.write("You leave the shop.")
                break
            else:
                # invalid option returns to shop menu
                self.io.write("LOL what are you trying to do??")

    def _trigger_random_event(self) -> None:
        assert self.player is not None
        events = self._event_pool()

        if len(self.used_events) == len(events):
            self.used_events.clear()

        remaining = [event for event in events if event not in self.used_events]
        chosen = self.rng.choice(remaining)
        self.used_events.add(chosen)
        trigger_used = {chosen}

        self.io.write(f"\n✨ Random Event: {chosen}!")
        self._apply_event(chosen)

        if self.rng.random() < 0.18:
            self.io.write("\n✨ Huh? Another Random Event?!")
            extra_events = self._event_pool()
            extra_events = [event for event in extra_events if event not in trigger_used]
            if not extra_events:
                extra_events = self._event_pool()
            extra = self.rng.choice(extra_events)
            self.used_events.add(extra)
            trigger_used.add(extra)
            self.io.write(f"✨ Random Event: {extra}!")
            self._apply_event(extra)

    def _maybe_trigger_endless_gimmick(self, enemy: Farm) -> None:
        assert self.player is not None
        last_turn = getattr(enemy, 'last_gimmick_turn', -999)
        if self.turn_count - last_turn < 3:
            return

        base = 0.24 if isinstance(enemy, Boss) else 0.14
        wave_scale = max(0, self.wave - STORY_END_WAVE)
        chance = base + min(0.18, wave_scale * 0.01)
        if self.rng.random() >= chance:
            return

        if isinstance(enemy, Boss):
            percent = 0.06 + min(0.12, wave_scale * 0.002)
            label = "Boss Siphon"
        else:
            percent = 0.04 + min(0.08, wave_scale * 0.0015)
            label = "Endless Hunger"

        damage = max(1, round(self.player.max_hp * percent))
        self.player.take_damage(damage)
        self.io.write(f"🔻 {enemy.name} triggers {label}, draining {damage} HP ({percent * 100:.1f}% of max)!")
        setattr(enemy, 'last_gimmick_turn', self.turn_count)

    def _event_pool(self) -> list[str]:
        events = list(RANDOM_EVENTS) + list(BAD_EVENTS)
        for wave_range, wave_events in WAVE_RANGE_EVENTS:
            if self.wave in wave_range:
                events.extend(wave_events)
                break
        return events

    def _event_scale(self) -> float:
        if not self.endless_mode:
            return 1.0
        extra = max(0, self.wave - STORY_END_WAVE)
        return min(2.0, 1.0 + extra * 0.03)

    def _scaled_percent(self, base: float) -> float:
        return min(0.45, base * self._event_scale())

    def _apply_event(self, event: str) -> None:
        event_map = {
            "Mysterious Merchant": self._event_mysterious_merchant,
            "Lightning Storm": self._event_lightning_storm,
            "Lost Cow Returns": self._event_lost_cow,
            "Strange Seed Sprouts": self._event_strange_seed,
            "A Trap": self._event_trap,
            "Wandering Bard": self._event_wandering_bard,
            "Locust Swarm": self._event_locust_swarm,
            "Irrigation Boom": self._event_irrigation_boom,
            "Moonlit Harvest": self._event_moonlit_harvest,
            "Butterfly Bloom": self._event_butterfly_bloom,
            "Soggy Furrows": self._event_soggy_furrows,
            "Cinder Drift": self._event_cinder_drift,
            "Charred Fence": self._event_charred_fence,
            "Gravel Gust": self._event_gravel_gust,
            "Rusted Plow": self._event_rusted_plow,
            "Sudden Hail": self._event_bad_event,
            "Rusty Pitchfork": self._event_bad_event,
            "Thorny Brambles": self._event_bad_event,
        }
        handler = event_map.get(event)
        if handler:
            handler(event)

    def _event_mysterious_merchant(self, _: str) -> None:
        if not self.player.merchant_skill_given:
            self.io.write("A mysterious merchant offers you a new skill.")
            self.player.add_new_skill(self.io)
            self.player.merchant_skill_given = True
        else:
            coins = self.rng.randint(3, 6)
            self.player.coins += coins
            self.io.write(f"The merchant slips you {coins} coins in thanks.")

    def _event_lightning_storm(self, _: str) -> None:
        self.io.write("A sudden lightning storm strikes your fields! You are hit.")
        amount = self.player.damage_percent(self._scaled_percent(0.18))
        self.io.write(f"{self.player.name} takes {amount} damage from the storm.")

    def _event_lost_cow(self, _: str) -> None:
        self.io.write("A lost cow returns with a kind moo and licks your wounds.")
        base_percent = self._scaled_percent(0.12)
        shield_percent = min(0.45, base_percent * 3)
        shield = max(1, round(self.player.max_hp * shield_percent))
        self.player.irrigation_shield = max(self.player.irrigation_shield, shield)
        coins = self.rng.randint(1, 3)
        self.player.coins += coins
        self.io.write(
            f"The cow's milk forms a gentle shield ({shield} damage absorbed, ~{shield_percent * 100:.1f}% of max) and you find {coins} coins in the pasture."
        )

    def _event_strange_seed(self, _: str) -> None:
        self.io.write("A strange seed sprouts, making your farm heartier.")
        inc = 15
        self.player.max_hp += inc
        self.player.health += inc
        self.io.write(f"Strange Seed: +{inc} max HP (now {self.player.max_hp}) and your health grows along with it.")

    def _event_trap(self, _: str) -> None:
        self.io.write("A hidden trap snaps at your heels!")
        amount = self.player.damage_percent(self._scaled_percent(0.2))
        self.io.write(f"{self.player.name} takes {amount} damage and stumbles.")

    def _event_wandering_bard(self, _: str) -> None:
        coins = self.rng.randint(3, 8)
        self.player.coins += coins
        self.io.write(f"A wandering bard sings of glory. You gain {coins} coins from compensation.")

    def _event_locust_swarm(self, _: str) -> None:
        self.io.write("A locust swarm devours your crops farm.")
        amount = self.player.damage_percent(self._scaled_percent(0.12))
        self.io.write(f"{self.player.name} loses {amount} HP to exhaustion.")

    def _event_irrigation_boom(self, _: str) -> None:
        self.io.write("Fresh irrigation surges through your fields in a rushing tide.")
        shield = max(1, round(self.player.max_hp * self._scaled_percent(0.1)))
        self.player.irrigation_attack_turns = max(self.player.irrigation_attack_turns, 2)
        self.player.irrigation_attack_bonus = max(self.player.irrigation_attack_bonus, 0.30)
        self.player.irrigation_shield = max(self.player.irrigation_shield, shield)
        self.io.write("Overflow Surge: next 2 attacks deal +30% damage.")
        self.io.write(f"A water shield forms for {shield} damage.")

    def _event_moonlit_harvest(self, _: str) -> None:
        coins = self.rng.randint(2, 5)
        self.player.coins += coins
        gold_chance = min(0.6, 0.35 * self._event_scale())
        if self.rng.random() < gold_chance:
            self.player.gold += 1
            self.io.write("The Moonlight reveals a hidden gold nugget!")
        self.io.write(f"You harvest {coins} coins under the moon.")

    def _event_butterfly_bloom(self, _: str) -> None:
        self.io.write("Butterflies swirl around your farm, stirring a fierce resolve.")
        coins = self.rng.randint(2, 5)
        self.player.coins += coins
        bonus = 3
        self.player.attack_power += bonus
        self.player.temp_attack_bonus += bonus
        self.io.write(f"You find {coins} coins and gain +{bonus} attack for this wave.")

    def _event_soggy_furrows(self, _: str) -> None:
        self.io.write("Soggy furrows slow you down.")
        amount = self.player.damage_percent(self._scaled_percent(0.1))
        self.io.write(f"You slog through and lose {amount} HP.")

    def _event_cinder_drift(self, _: str) -> None:
        self.io.write("Cinder drift coats the crops in ash.")
        amount = self.player.damage_percent(self._scaled_percent(0.14))
        self.io.write(f"Heat drains {amount} HP.")

    def _event_charred_fence(self, _: str) -> None:
        self.io.write("A charred fence collapses—repair costs mount.")
        coins = self.rng.randint(2, 4)
        self.player.coins = max(0, self.player.coins - coins)
        self.io.write(f"You spend {coins} coins on repairs.")

    def _event_gravel_gust(self, _: str) -> None:
        self.io.write("A gravel gust whips across the ridge.")
        amount = self.player.damage_percent(self._scaled_percent(0.1))
        self.io.write(f"You take {amount} damage.")

    def _event_rusted_plow(self, _: str) -> None:
        self.io.write("You salvage a rusted plow for scrap.")
        coins = self.rng.randint(3, 6)
        self.player.coins += coins
        self.io.write(f"You gain {coins} coins.")

    def _event_bad_event(self, event: str) -> None:
        cleaned = event.strip()
        self.io.write(f"⚠️ {cleaned}!")
        if cleaned == "Sudden Hail":
            amount = self.player.damage_percent(self._scaled_percent(0.12))
            self.io.write(f"Hail pummels your roof. You take {amount} damage.")
        elif cleaned == "Rusty Pitchfork":
            amount = self.player.damage_percent(self._scaled_percent(0.1))
            self.io.write(f"You nick yourself on a rusty pitchfork. -{amount} HP.")
        elif cleaned == "Thorny Brambles":
            amount = self.player.damage_percent(self._scaled_percent(0.08))
            self.io.write(f"Brambles scratch you up. -{amount} HP.")
        else:
            amount = self.player.damage_percent(self._scaled_percent(0.1))
            self.io.write(f"{cleaned} leaves you battered. -{amount} HP.")

def main() -> None:
    game = Game()
    game.start()

if __name__ == "__main__":
    main()
