from sc2 import bot_ai
from sc2.bot_ai import BotAI               # parent class we inherit from
# difficulty for bots, race for the 1 of 3 races
from sc2.data import Difficulty, Race
# function that facilitates actually running the agents in games
from sc2.main import run_game
# wrapper for whether or not the agent is one of your bots, or a "computer" player
from sc2.player import Bot, Computer
# maps method for loading maps to play in.
from sc2 import maps
from sc2.ids.unit_typeid import UnitTypeId  # Contains unitTypeIds
from sc2.ids.ability_id import AbilityId
import random
import numpy as np
from sc2.unit import Unit
from sc2.position import Point2, Point3

# inhereits from BotAI (part of BurnySC2)
class Overmind(BotAI):
    MAX_OVERLORDS = 14
    MAX_DRONES    = 80
    MIN_DRONES    = 20
    MAX_DEF_SPINECRAWLERS = 2

    async def on_step(self, iteration: int):
        #print(f"This is my bot in iteration {iteration}, workers: {self.workers}, idle workers: {self.workers.idle}, supply: {self.supply_used}/{self.supply_cap}")
        # print(f"{iteration}")
        # begin logic:
        await self.distribute_workers()
        await self.make_drones()
        await self.make_hatchery()
        await self.make_overlords()
        await self.make_spawningpool()
        await self.make_extractor()
        await self.make_zerglings()
        await self.make_queens()
        await self.inject_hatchery()
        await self.distribute_overlords()
        await self.make_spinecrawlers()

    async def make_spinecrawlers(self):
        if self.units(UnitTypeId.DRONE).amount > self.MIN_DRONES:
            hatcherys = self.townhalls
            for hatchery in hatcherys:
                #print(f"close spinecrawlers: {self.structures(UnitTypeId.SPINECRAWLER).closer_than(10, hatchery.position.to2).amount} pending: {self.already_pending(UnitTypeId.SPINECRAWLER)}")
                #print(f"pos {hatchery.position} pos2 {hatchery.position.to2} pos3 {hatchery.position.to3}")
                print(f"if {self.structures(UnitTypeId.SPINECRAWLER).closer_than(10,hatchery.position.to2).amount} <= {self.MAX_DEF_SPINECRAWLERS}")
                if self.structures(UnitTypeId.SPINECRAWLER).closer_than(10, hatchery.position.to2).amount < self.MAX_DEF_SPINECRAWLERS:
                    pos = await self.find_placement(UnitTypeId.SPINECRAWLER,hatchery.position.to2,max_distance=10)
                    drone = self.workers.closest_to(hatchery)
                    if self.can_afford(UnitTypeId.SPINECRAWLER):
                        drone.build(UnitTypeId.SPINECRAWLER, pos)

    async def inject_hatchery(self):
        if self.units(UnitTypeId.QUEEN).exists:
            hatcherys = self.townhalls
            for hatchery in hatcherys:
                closest_queen = self.units(UnitTypeId.QUEEN).closest_to(hatchery)
                if (
                    closest_queen.is_idle
                    and closest_queen.energy > 50
                    ):
                    closest_queen(AbilityId.EFFECT_INJECTLARVA,hatchery)

    async def distribute_overlords(self):
        # self.draw_creep_pixelmap()
        overlords = self.units(UnitTypeId.OVERLORD)
        #MOVE RANDOMLY
        for overlord in overlords:
            if overlord.is_idle:
                overlord.move(random.choice(self.expansion_locations_list))
        #PROTECT ZE OVERLORDS
        for overlord in overlords:
            #print(f"Overlord: {overlord}, Health_Percentage: {overlord.health_percentage}")
            if overlord.health_percentage < 1:
                overlord.move(self.townhalls.random)

    def draw_creep_pixelmap(self):
        for (y, x), value in np.ndenumerate(self.state.creep.data_numpy):
            p = Point2((x, y))
            h2 = self.get_terrain_z_height(p)
            pos = Point3((p.x, p.y, h2))
            # Red if there is no creep
            color = Point3((255, 0, 0))
            if value == 1:
                # Green if there is creep
                color = Point3((0, 255, 0))
            self.client.debug_box2_out(
                pos, half_vertex_length=0.25, color=color)

    async def make_queens(self):
        #print(f"Queens: {self.units(UnitTypeId.QUEEN).amount}, Bases: {self.structures(UnitTypeId.HATCHERY).amount}")
        if (
            self.can_afford(UnitTypeId.QUEEN)
            and self.units(UnitTypeId.QUEEN).amount < self.structures(UnitTypeId.HATCHERY).amount
            and not self.already_pending(UnitTypeId.QUEEN) > 0
        ):
            self.townhalls.random.build(UnitTypeId.QUEEN)

    async def make_hatchery(self):

        if self.units(UnitTypeId.DRONE).amount >= self.structures(UnitTypeId.HATCHERY).amount * 22:
            hatchery_location = await self.get_next_expansion()
            drone = self.workers.closest_to(hatchery_location)
            drone.build(UnitTypeId.HATCHERY, hatchery_location)

    async def make_zerglings(self):
        if (
            self.units(UnitTypeId.LARVA).exists
            and self.can_afford(UnitTypeId.ZERGLING)
            and self.units(UnitTypeId.ZERGLING).amount < self.structures(UnitTypeId.HATCHERY).amount * 22
        ):
            self.units(UnitTypeId.LARVA).random.train(UnitTypeId.ZERGLING)

    async def make_extractor(self):
        # game does not like when hatchery is destroyed
        hatchery = self.townhalls.random
        if hatchery.assigned_harvesters >= 16:
            close_vgs = self.vespene_geyser.closer_than(10, hatchery)
            for vg in close_vgs:
                if self.can_afford(UnitTypeId.EXTRACTOR):
                    drone = self.workers.closest_to(vg)
                    drone.build(UnitTypeId.EXTRACTOR, vg)

    async def make_spawningpool(self):
        if (
            self.can_afford(UnitTypeId.SPAWNINGPOOL)
            and not self.structures(UnitTypeId.SPAWNINGPOOL).exists
            and self.townhalls.amount >= 1
        ):
            pos = await self.find_placement(UnitTypeId.SPAWNINGPOOL, self.townhalls.ready.random.position.to2, max_distance=10)
            if pos is not None:
                drone = self.workers.closest_to(pos)
                if self.can_afford(UnitTypeId.SPAWNINGPOOL):
                    drone.build(UnitTypeId.SPAWNINGPOOL, pos)

    async def make_overlords(self):
        #print(f"ovlamount {self.units(UnitTypeId.OVERLORD).amount} max_overlords {self.MAX_OVERLORDS} overlordpending: {self.already_pending(UnitTypeId.OVERLORD)}")
        if (
            self.supply_left < 3
            and self.can_afford(UnitTypeId.OVERLORD)
            and self.units(UnitTypeId.LARVA).exists
            and self.units(UnitTypeId.OVERLORD).amount + self.already_pending(UnitTypeId.OVERLORD) < self.MAX_OVERLORDS
        ):
            self.units(UnitTypeId.LARVA).random.train(UnitTypeId.OVERLORD)

    async def make_drones(self):
        if (
            self.units(UnitTypeId.LARVA).exists
            and self.can_afford(UnitTypeId.DRONE)
            and self.units(UnitTypeId.DRONE).amount < self.structures(UnitTypeId.HATCHERY).amount * 22
            and self.units(UnitTypeId.DRONE).amount < 80
        ):
            self.units(UnitTypeId.LARVA).random.train(UnitTypeId.DRONE)


run_game(                                   # run_game is a function that runs the game.
    maps.get("2000AtmospheresAIE"),         # the map we are playing on
    [Bot(Race.Zerg, Overmind()),       # runs our coded bot, protoss race, and we pass our bot object
     Computer(Race.Terran, Difficulty.Easy)],  # runs a pre-made computer agent, zerg race, with a hard difficulty.
    # When set to True, the agent is limited in how long each step can take to process.
    realtime=False,
)

# Don't make multiple overlords even if supply is low because you make 3 immediately in the beginning uncessisarily
# do like.... up to 1 per base or something

# Issue with all the drones immediately running to the second base to make spinecrawlers, but then they make like 10
# because they've already been ordered to - figure out how to fix