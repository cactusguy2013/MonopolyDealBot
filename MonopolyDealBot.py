import discord
import random
from discord.ext import commands

bot = commands.Bot(command_prefix='!')

cards = []
draw_pile = []
discard_pile = []
players = []
emojis = []
colours = {}
turn = -1
cards_played = 0
main_channel = 0


class Player:
    def __init__(self, user, name):
        self.user = user
        self.table = []
        self.hand = []
        self.bank = []
        self.handdm = None
        self.tabledm = None
        self.name = name
        for i in range(20):
            self.table.append([])


class Colour:
    def __init__(self, name, rent_prices, emoji):
        self.name = name
        self.rent_prices = rent_prices
        self.emoji = emoji


class Card:
    def __init__(self, name, card_type, value, colours, description):
        self.name = name
        self.card_type = card_type
        self.value = value
        self.colours = colours
        self.description = description


@bot.event
async def on_ready():
    print("Bot is ready")


@bot.command(aliases=["Join"])
async def join(ctx, name=""):
    if name == "":
        players.append(Player(ctx.author, ctx.author.display_name))
    else:
        players.append(Player(ctx.author, name))
    await ctx.send(f"<@{ctx.author.id}> is in the game")


@bot.command(aliases=["Name"])
async def name(ctx, name):
    player = get_player(ctx.author)
    player.name = name
    await ctx.send("Name updated")


@bot.command(aliases=["Start"])
async def start(ctx):
    global main_channel
    global turn
    main_channel = ctx.channel
    await main_channel.send(f"Game is commencing with {len(players)} players")

    parse_colour_data(ctx)
    parse_card_data()
    draw_pile.extend(cards)
    random.shuffle(draw_pile)

    for player in players:
        dm_channel = await player.user.create_dm()
        async for message in dm_channel.history(limit=10000):
            if message.author == bot.user:
                await message.delete()

        await show_table(player)
        await draw_cards(player, 5)

    await end_turn(None)


@bot.command(aliases=["End_turn", "end", "End", "done", "Done"])
async def end_turn(ctx):
    global turn
    global cards_played
    message = ""
    if ctx is not None:
        ctx_player = get_player(ctx.author)
        message += f'<@{ctx_player.user.id}> ends turn holding {len(ctx_player.hand)} cards (max 7)'
        await show_hand(ctx_player)

    if ctx is not None and ctx.author != players[turn % len(players)].user:
        await ctx.send("Only the person playing can use this command")
        return

    turn += 1
    player = players[turn % len(players)]
    cards_played = 0
    await main_channel.send(message + f"\n\nNow it's <@{player.user.id}> 's turn")

    await draw_cards(player, 2)


@bot.command(aliases=["Draw2", "Draw_2", "draw_2", "Draw", "draw"])
async def draw2(ctx):
    player = get_player(ctx.author)
    await draw_cards(player, 2)


async def draw_cards(player, amount):
    for i in range(amount):
        if len(draw_pile) == 0:
            draw_pile.extend(discard_pile)
            random.shuffle(draw_pile)
            discard_pile.clear()
        player.hand.append(draw_pile.pop())

    await show_hand(player)


@bot.command(aliases=["Discard"])
async def discard(ctx, *name):
    player = get_player(ctx.author)

    card = get_card_in_hand(player, name)

    if card == "Not found":
        await ctx.send("Could not find the card in your hand")
        return

    discard_pile.append(card)
    player.hand.remove(card)
    await show_hand(player)


@bot.command(aliases=["Place"])
async def place(ctx, *args):
    global cards_played
    args = await get_ordered_args(args)
    set_num = None
    name = ""
    if args[0].isdigit():
        set_num = int(args[0])
        name = args[1:]
    else:
        name = args[:]
    player = get_player(ctx.author)
    card = get_card_in_hand(player, name)

    if set_num == None:
        for i in range(len(player.table)):
            if len(player.table[i]) == 0:
                set_num = i
                break

    if card == "Not found":
        await ctx.send("Could not find the card in your hand")
        return

    if card.card_type != "Property" and card.name != "Hotel" and card.name != "House":
        await ctx.send("You can only place properties, use '!bank' for money and '!play' for action cards")
        return

    player.table[set_num].append(card)
    player.hand.remove(card)

    if player == players[turn % len(players)]:
        cards_played += 1

    for p in players:
        await show_table(p)
    await main_channel.send(f'<@{player.user.id}> places **{card.name}** ({cards_played}/3)')


@bot.command(aliases=["Bank, Store, store"])
async def bank(ctx, *name):
    global cards_played
    player = get_player(ctx.author)
    card = get_card_in_hand(player, name)

    if card == "Not found":
        await ctx.send("Could not find the card in your hand")
        return

    if card.card_type != "Money" and card.card_type != "Action":
        await ctx.send("You can only bank money and action cards, use '!place' for properties")
        return

    player.bank.append(card)
    player.hand.remove(card)

    if player == players[turn % len(players)]:
        cards_played += 1

    for p in players:
        await show_table(p)
    await main_channel.send(f'<@{player.user.id}> banks **{card.name}** ({cards_played}/3)')


@bot.command(aliases=["Play, Use, use"])
async def play(ctx, *name):
    global cards_played
    player = get_player(ctx.author)
    card = get_card_in_hand(player, name)

    if card == "Not found":
        await ctx.send("Could not find the card in your hand")
        return

    if card.card_type != "Action" or card.name == "Hotel" or card.name == "House":
        await ctx.send("You can only play action card, use '!place' for properties and '!bank' for money")
        return

    player.hand.remove(card)
    discard_pile.append(card)

    if card.name == "Pass Go":
        await draw_cards(player, 2)

    if player == players[turn % len(players)]:
        cards_played += 1

    await show_hand(player)
    await main_channel.send(f'<@{player.user.id}> plays **{card.name}**: *{card.description}* ({cards_played}/3)')
    if card.name.startswith("Rent"):
        rent = calculate_rent(card, player)
        await main_channel.send(f"The rent is calculated to be ${rent}M")


def calculate_rent(card, player):
    max_rent = 0
    for colour in card.colours:
        max_per_colour = 0
        for s in player.table:
            colour_count = 0
            house = False
            hotel = False
            for c in s:
                if colour in c.colours:
                    colour_count += 1
                if c.name == "House":
                    house = True
                if c.name == "Hotel":
                    hotel = True
            rent = 0
            if colour_count > 0:
                rent = int(colour.rent_prices[min(colour_count - 1, len(colour.rent_prices) - 1)])
            if house:
                rent += 3
                if hotel:
                    rent += 4
            max_per_colour = max(rent, max_per_colour)
        max_rent = max(max_per_colour, max_rent)
    return max_rent


def get_card_in_hand(player, name):
    name = " ".join(name)
    card = "Not found"

    for c in player.hand:
        if c.name.lower().replace("'", "") == name.lower().replace("'", ""):
            card = c

    return card


@bot.command(aliases=["Pay"])
async def pay(ctx, *args):  # target_player, *moneys
    args = await get_ordered_args(args)
    player = get_player(ctx.author)
    target_player = get_player(await get_user(args[0]))
    moneys = args[1:]
    cards = []

    if target_player is None:
        await ctx.send("Could not find the player mentioned")
        return

    for value in moneys:
        value = int(value)

    for money in moneys:
        index_to_pop = -1
        for i in range(len(player.bank)):
            if player.bank[i].value == money:
                cards.append(player.bank[i])
                index_to_pop = i
                break
        if index_to_pop != -1:
            player.bank.pop(index_to_pop)

    # Couldn't find one or more arguments
    if len(cards) != len(moneys):
        await ctx.send("Couldn't find cards that satisfy all values given")
        player.bank.extend(cards)
        return

    target_player.bank.extend(cards)
    payed = 0
    for money in moneys:
        payed += int(money)
    for p in players:
        await show_table(p)
    await main_channel.send(f"<@{player.user.id}> payed <@{target_player.user.id}> **${payed}M**")


@bot.command(aliases=["Move"])
async def move(ctx, *args):  # to-set *name
    args = await get_ordered_args(args)
    to_set = args[0]
    name = args[1:]
    player_at = f"<@!{ctx.author.id}>"
    await move_card(ctx, player_at, player_at, to_set, *name)


@bot.command(aliases=["Give"])
async def give(ctx, *args):  # target_player, *name
    args = await get_ordered_args(args)
    player_at = f"<@!{ctx.author.id}>"
    target_player = args[0]
    name = args[1:]
    card = await move_card(ctx, player_at, target_player, 19, *name)
    if card is not None:
        target_user = await get_user(target_player)
        await main_channel.send(f'{player_at} gives <@{target_user.id}> **{card.name}**')


@bot.command(aliases=["Take"])
async def take(ctx, *args):  # target_player, to_set, *name
    args = await get_ordered_args(args)
    player_at = f"<@!{ctx.author.id}>"
    # target_player = args[0]
    to_set = args[0]
    name = args[1:]

    target_player = None
    for player in players:
        for card_set in player.table:
            for card in card_set:
                if card.name.lower() == " ".join(name).lower():
                    target_player = player.name

    card = await move_card(ctx, target_player, player_at, to_set, *name)
    if card is not None:
        target_user = await get_user(target_player)
        await main_channel.send(f'{player_at} takes **{card.name}** from <@{target_user.id}>')


@bot.command(
    aliases=["TakeSet", "takeset", 'Takeset', 'Take_Set', 'Take_set', 'DealBreaker', 'Dealbreaker', 'dealbreaker',
             'Deal_Breaker', 'Deal_breaker', 'deal_breaker'])
async def take_set(ctx, *args):  # target_player, from-set, to_set
    args = await get_ordered_args(args)
    target_player = get_player(await get_user(args[0]))
    from_set = int(args[1])
    to_set = int(args[2])
    player = get_player(ctx.author)

    if target_player is None:
        await ctx.send("Could not find the player mentioned")
        return

    player.table[to_set].extend(target_player.table[from_set])
    target_player.table[from_set].clear()
    for p in players:
        await show_table(p)
    await main_channel.send(f'<@{player.user.id}> takes a full set from <@{target_player.user.id}>')


@bot.command(aliases=["Shift", "shift", "Move_card", "Move_Card", "Transfer", "transfer"])
async def move_card(ctx, from_player, to_player, to_set, *name):
    name = " ".join(name)
    card = "Not found"
    from_player = get_player(await get_user(from_player))
    to_player = get_player(await get_user(to_player))
    to_set = int(to_set)

    if from_player is None:
        await ctx.send("Could not find the player mentioned")
        return None

    if to_player is None:
        await ctx.send("Could not find the player mentioned")
        return None

    from_set = 0
    for s in from_player.table:
        for c in s:
            if c.name.lower() == name.lower():
                card = c
                break
        # This breaks the outer loop when card is found
        else:
            from_set += 1
            continue
        break

    if card == "Not found":
        await ctx.send("Could not find the card in your properties")
        return None

    to_player.table[to_set].append(card)
    from_player.table[from_set].remove(card)
    for p in players:
        await show_table(p)
    return card


async def get_ordered_args(args):
    # Orders args players, then nums, then the card name
    players = []
    nums = []
    name = []

    for arg in args:
        user = await get_user(arg)
        if get_player(user) is not None:
            players.append(arg)
        elif arg.isdigit():
            nums.append(arg)
        else:
            name.append(arg)

    ordered_args = []
    ordered_args.extend(players)
    ordered_args.extend(nums)
    ordered_args.extend(name)

    return ordered_args


async def show_table(player):
    if player.tabledm is not None:
        await player.tabledm.delete()
        player.tabledm = None

    message = "**The Table:**\n"
    for p in players:
        other_name = ""
        if p.name != p.user.display_name:
            other_name = f" ({p.name})"
        message += f"<@{p.user.id}>{other_name}'s properties:\n"
        i = 0
        for card_set in p.table:
            if len(card_set) > 0:
                message += f"Set {i}:\n"
                for card in card_set:
                    emojis = ""
                    for colour in card.colours:
                        emojis += f"{colour.emoji}"
                    message += card.name + f" {emojis} (${card.value}M)\n"
            i += 1

        message += f"\n<@{p.user.id}>{other_name}'s bank:\n"
        for card in p.bank:
            if card.card_type == "Money":
                message += card.name + "\n"
            else:
                message += card.name + f" (${card.value}M)\n"
        message += "\n"

    dm_channel = await player.user.create_dm()
    message = await dm_channel.send(message)
    player.tabledm = message

    await show_hand(player)


async def show_hand(player):
    if len(player.hand) == 0:
        return

    if player.handdm is not None:
        try:
            await player.handdm.delete()
        except:
            print("This makes no sense")
        player.handdm = None

    # dm user their hand
    dm_channel = await player.user.create_dm()
    text = "**Your Hand:**\n"
    for i in range(len(player.hand)):
        card = player.hand[i]
        emojis = ""
        for colour in card.colours:
            emojis += f"{colour.emoji}"
        if card.card_type == "Property":
            text += f"{i + 1}: {card.name} {emojis} (${card.value}M)\n"
        elif card.card_type == "Action":
            text += f"{i + 1}: {card.name} {emojis} (${card.value}M)\n"
        else:
            text += f"{i + 1}: {card.name}\n"

    if player == players[turn % len(players)] and turn != -1:
        text += f"\n**Your turn ({cards_played}/3)**"

    message = await dm_channel.send(text)
    player.handdm = message


@bot.command(aliases=["Colours", "colours", "Prices"])
async def prices(ctx):
    message = "Rent prices:\n"
    for colour in colours:
        message += f"{colours[colour].emoji}: $"
        message += "M, $".join(colours[colour].rent_prices)
        message += "M\n"
    await ctx.send(message)


@bot.command(aliases=["Info", "Details", "details"])
async def info(ctx, *name):
    name = " ".join(name)
    card = "Not found"

    for c in cards:
        if c.name.lower() == name.lower():
            card = c

    if card == "Not found":
        await ctx.send("Could not find the card in your properties")
        return

    message = f"Name: {card.name}\n"
    message += f"Type: {card.card_type}\n"
    message += f"Colours: {card.colours}\n"
    message += f"Value: {card.value}\n"
    message += f"Description: *{card.description}*\n"

    await ctx.send(message)


@bot.command(aliases=["Commands"])
async def commands(ctx):
    message = "Commands:\n"
    message += "!join\n"
    message += "!start\n"
    message += "!end\n"
    message += "!place card_name OR !place set card_name\n"
    message += "!bank card_name\n"
    message += "!play card_name\n"
    message += "!move to_set card_name\n"
    message += "!give @player card_name\n"
    message += "!take @player to_set card_name\n"
    message += "!takeset @player from_set to_set\n"
    message += "!discard card_name\n"
    message += "!prices\n"
    message += "!info card_name\n"
    await ctx.send(message)


def get_player(user):
    for player in players:
        if player.user == user:
            return player
    return None


async def get_user(text):
    if text[0] == "<":
        return await bot.fetch_user(int(text[3:-1]))
    for player in players:
        if player.name.lower() == text.lower():
            return player.user
        if player.user.display_name.lower() == text.lower():
            return player.user


def parse_card_data():
    f = open("MonopolyDealCards.txt", "r")
    args = []
    for line in f:
        tokens = line.split(": ")

        if line == "\n":
            colour_strings = args[3].split(", ")
            colour_list = []
            for s in colour_strings:
                if s == "":
                    continue
                colour_list.append(colours[s])
            card = Card(args[0], args[1], args[2], colour_list, args[4])
            cards.append(card)
            args = []
        elif len(tokens) >= 2:
            args.append(tokens[1].strip(" \n"))
        else:
            args.append("")


def parse_colour_data(ctx):
    f = open("MonopolyDealColours.txt", "r")
    for line in f:
        tokens = line.split(": ")
        if tokens[0] == "\n":
            continue
        values = tokens[1].strip(" \n").split(", ")
        for value in values:
            value = int(value)
        emoji = None
        for e in ctx.guild.emojis:
            name = tokens[0].replace(" ", "_").lower()
            if e.name == name:
                emoji = e
        colours[tokens[0]] = Colour(tokens[0], values, emoji)


bot.run("REMOVED")
