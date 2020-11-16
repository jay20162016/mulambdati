from expr import Application, Variable, Abstraction
from monad_io import EvalIO
from abc import ABC, abstractmethod
import asyncio

class Action:
    def __init__(self, combinators, fvs, abstractions, deck_combine, eval_terms):
        self.combinators = combinators
        self.fvs = fvs # [str]
        self.abstractions = abstractions # [(int, str)]
        self.deck_combine = deck_combine
        self.eval_terms = eval_terms

    def __str__(self):
        return\
            f"Action(combinators={self.combinators}, " +\
            "fvs={self.fvs}, abstractions={self.abstractions}, " +\
            "deck_combine={self.deck_combine}, eval_terms={self.eval_terms})"

    def run(self, game, player_idx):
        player = game.players[player_idx]

        player.mana += 1
        for p in self.combinators:
            price, _name, term = game.combinators[p]
            player.mana -= price
            player.deck.append(term)

        for fv in self.fvs:
            player.deck.append(Variable(fv))
            player.mana -= 2

        for row, name in self.abstractions:
            player.deck[row] = Abstraction(name, player.deck[row])
            player.mana -= 2

        for (s1, s2) in self.deck_combine:
            player.deck[s1] = Application(player.deck[s1], player.deck[s2]).whnf()
            del player.deck[s2]

        for e in self.eval_terms:
            term = EvalIO(game.layout, player.deck[e])
            print("Player {player_idx} running {term}")
            player.deck[e] = term.whnf()

class Player(ABC):
    def __init__(self, sec_token, health, mana):
        self.sec_token = sec_token # Given to a client on game start, kept secret and used to """authenticate"""
        self.health = health
        self.mana = mana
        self.deck = []

    @abstractmethod
    async def update_state(self, game):
        pass

    @abstractmethod
    async def get_action(self):
        pass

    @abstractmethod
    async def tell_action(self, action):
        pass

class ConsolePlayer(Player):
    def __init__(self, sec_token, health, mana, f_in, f_out):
        super(ConsolePlayer, self).__init__(sec_token, health, mana)

        self.f_out = f_out
        self.f_in = f_in

        self.purchasable_combinators = []

    async def update_state(self, game):
        self.purchasable_combinators = game.combinators
        for pl, name in [(game.players[0], "Player one"), (game.players[1], "Player two")]:
            tag = ""
            if pl is self:
                tag = " (you!)"
            await self.f_out.write(f"{name}{tag}:\n")
            await self.f_out.write(f"    Health/Mana: {pl.health}/{pl.mana}\n")
            await self.f_out.write("    Deck:\n")
            for i, card in enumerate(pl.deck):
                await self.f_out.write(f"        {i}: {card}\n")

        await self.f_out.flush()

    async def tell_action(self, action):
        await self.f_out.write(f"[!! {action} !!]\n")
        await self.f_out.flush()

    async def get_action(self):
        await self.f_out.write("Your turn!\n")
        await self.f_out.write("Combinators:\n")
        for i, (price, name, term) in enumerate(self.purchasable_combinators):
            await self.f_out.write(f"    {i}: {name}: costs {price}𐌼\n")

        await self.f_out.write("Purchase combinators? (comb),* ")
        await self.f_out.flush()

        combinators = [int(x) for x in (await self.f_in.readline()).strip().split(",") if x]

        await self.f_out.write("Purchase free variables (2𐌼 per variable) (name),*? ")
        await self.f_out.flush()

        fvs = [x for x in (await self.f_in.readline()).strip().split(",") if x]

        await self.f_out.write("Abstractions (2𐌼)  (enter (row-name2caputre)-*),* ")
        await self.f_out.flush()

        abstractions = [(int(x.split("-")[0]), x.split("-")[1]) for x in (await self.f_in.readline()).strip().split(",") if x]

        await self.f_out.write("Combines (f-x),* ")
        await self.f_out.flush()
        combines = [(int(y) for y in x.split("-")) for x in (await self.f_in.readline()).strip().split(",") if x]

        await self.f_out.write("Evals (f),* ")
        await self.f_out.flush()
        evals = [int(x) for x in (await self.f_in.readline()).strip().split(",") if x]

        return Action(combinators, fvs, abstractions, combines, evals)
