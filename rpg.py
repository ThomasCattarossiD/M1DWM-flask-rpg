import math
import random
from datetime import date


class Stat:
    """ stat of the player """

    def __init__(self, statsdict):
        self._strength = statsdict['strength']
        self._magic = statsdict['magic']
        self._agility = statsdict['agility']
        self._speed = statsdict['speed']
        self._charisma = statsdict['charisma']
        self._chance = statsdict['chance']
        self._endurance = random.randint(self.strength + self._agility, 2 * (self.strength + self._agility))
        self._life_point = random.randint(self._endurance, 2 * self._endurance)
        self._attack = self.strength + self._magic + self._agility
        self._defense = self._agility + self._speed + self._endurance

    @property
    def strength(self):
        """Getter for strength."""
        return self._strength

    @strength.setter
    def strength(self, value):
        strength_difference = value - self._strength

        """Setter for strength."""
        if value < 0:
            raise ValueError("Strength cannot be negative.")
        self._strength = value
        # Optionally, recalculate derived attributes if strength changes
        self._endurance += strength_difference
        self._attack += strength_difference

    @property
    def life_point(self):
        return self._life_point

    @property
    def speed(self):
        return self._speed

    @property
    def agility(self):
        return self._agility

    @property
    def chance(self):
        return self._chance

    @property
    def attack(self):
        return self._attack

    @property
    def defense(self):
        return self._defense

    def __str__(self):
        return str(self.__dict__)


class Classe:
    """ class type """

    def __init__(self, name, stat):
        self._name = name
        self._stat = stat

    def __str__(self):
        return str(self._name)


class Race:
    """ race type """

    def __init__(self, name, stat):
        self._name = name
        self._stat = stat

    def __str__(self):
        return str(self._name)

    @property
    def stat(self):
        return self._stat

    @property
    def name(self):
        return self._name


class Bag:
    """ Bag class to save Items """

    def __init__(self, args):
        self._sizeMax = args['sizeMax']
        self._lItems = args['items']
        self._size = len(self._lItems)

    def addItem(self, i):
        if self._size < self._sizeMax:
            self._lItems.append(i)
            self._size += 1
        else:
            return False

    def delItem(self, i):
        self._lItems.pop(i)
        self._size -= 1

    def __str__(self):
        output = ""
        for i in self._lItems:
            output += str(i)
        return output

    @property
    def lItems(self):
        return self._lItems


class Avatar:
    """ general class """
    id = 0

    def __init__(self, targs):
        self._nom = targs['name']
        self._race = targs['race']
        self._classe = targs['classe']
        self._bag = targs['bag']
        self._equipment = targs['equipment']
        self._element = targs['element']
        self._lvl = 1
        self._stat = Stat({'strength': 1, 'magic': 1, 'agility': 1, 'speed': 1, 'charisma': 0, 'chance': 0})
        Avatar.id += 1
        self.sumstat()
        self._life = self._stat.life_point

    def getBag(self):
        return self._bag.lItems

    def initiative(self):
        inmin = self._stat.speed
        inmax = self._stat.agility + self._stat.chance + self._stat.speed
        return random.randint(inmin, inmax)

    def damages(self):
        critique = random.randint(0, self._stat.chance)
        min = 0
        max = self._stat.attack
        if critique > self._stat.chance / 2:
            print("full damages")
            maxDam = random.randint(max, 2 * max)
        else:
            maxDam = random.randint(min, max)
        print(self._nom + " done " + str(maxDam))
        return maxDam

    def defense(self, v):
        min_dodge = self._stat.agility
        max_dodge = self._stat.agility + self._stat.chance + self._stat.speed
        duck = random.randint(min_dodge, max_dodge)

        # Actual damage calculation
        damage = v

        # Dodge mechanics
        if duck == max_dodge:
            print("the shot is completely dodged")
            damage = 0
        elif duck > max_dodge / 2:
            print("partial dodge")
            damage //= 2  # Integer division to avoid floating point

        # Defense reduction
        damage = max(0, damage - self._stat.defense)

        # Life point reduction
        self._life = max(0, self._life - damage)

        print("life point: ", self._life, " / ", self._stat.life_point)

        if self._life == 0:
            print("You are dead")

    def __str__(self):
        show = str(self._nom)
        return show

    @property
    def nom(self):
        return self._nom

    @property
    def life(self):
        return self._life

    @life.setter
    def life(self, value):
        """
        Setter for life points with validation.
        Ensures life doesn't exceed maximum life points and isn't negative.
        """
        # Ensure life doesn't go below 0
        if value < 0:
            self._life = 0
        # Ensure life doesn't exceed maximum life points
        elif value > self._stat.life_point:
            self._life = self._stat.life_point
        else:
            self._life = value

    @property
    def bag(self):
        return self._bag

    def sumstat(self):
        equiment = 0
        for i in self._stat.__dict__:
            for j in self._equipment:
                equiment += j.stat.__dict__[i]
            self._stat.__dict__[i] = self._race.stat.__dict__[i] + self._classe.stat.__dict__[i] + equiment


class Item:
    """ object class """
    nbr = 0

    def __init__(self, targs, stat):
        self._name = targs['name']
        self._type = targs['type']
        self._space = targs['space']
        self._stat = stat
        Item.nbr += 1

    def __str__(self):
        return str(self._name)

    @property
    def stat(self):
        return self._stat

    @property
    def name(self):
        return self._name


class Equipment(Item):
    def __init__(self, targs, stat):
        Item.__init__(self, targs, stat)
        self._lClasses = targs['classList']
        self._place = targs['place']


class Mobs(Avatar):
    def __init__(self, targs):
        Avatar.__init__(self, targs)
        self._type = targs["type"]

    def __str__(self):
        output = "Mobs " + self._type + " " + self._nom
        return output


class Quest:
    """ class for manage quest """

    def __init__(self, targs):
        self._lAvatar = targs['lAvatar']
        self._lvl = targs['lvl']
        self._itemGift = targs['gift']

    def run(self, hero):
        round = 1
        output = ""

        if len(self._lAvatar) == 1:
            # PVP MODE (remains the same as original)
            output += "### PVP MODE ####"
            print("### PVP MODE ####")
            player = self._lAvatar[0]
            output += "\n" + player.nom + " VS " + hero.nom
            print(player.nom + " VS " + hero.nom)

            original_hero_life = hero.life  # Store original life points

            while (player.life > 0) and (hero.life > 0):
                output += "\n" + "Round " + str(round)
                print("# Round " + str(round) + " # ")
                print("# PV de " + hero.nom + " " + str(hero.life))
                output += "\n" + "# PV de " + hero.nom + " " + str(hero.life)
                print("# PV de " + player.nom + " " + str(player.life))
                output += "\n" + "# PV de " + player.nom + " " + str(player.life)

                if player.initiative() > hero.initiative():
                    output += "\n" + player.nom + " begin"
                    print(player.nom + " begin")
                    hero.defense(player.damages())
                    if hero.life <= 0:
                        output += "\n" + player.nom + " win"
                        print(player.nom + " win")
                    else:
                        player.defense(hero.damages())
                else:
                    output += "\n" + hero.nom + " begin"
                    print(hero.nom + " begin")
                    player.defense(hero.damages())
                    if player.life <= 0:
                        output += "\n" + hero.nom + " win"
                        print(hero.nom + " win")
                    else:
                        hero.defense(player.damages())

                round += 1

            if hero.life <= 0:
                output += "\n" + player.nom + " win"
                print(player.nom + " win")
            else:
                output += "\n" + hero.nom + " win"
                print(hero.nom + " win")
                hero.setXP(10 * self._lvl)
                hero.bag.addItem(self._itemGift)

        else:
            output += "\n" + "### Quest MODE ####"
            print("### Quest MODE ####")

            original_hero_life = hero.life  # Store original life points

            for player in self._lAvatar:
                # Reset hero's life points before each fight
                hero.life = original_hero_life

                output += "\n" + player.nom + " VS " + hero.nom
                print(player.nom + " VS " + hero.nom)

                round = 1  # Reset round for each fight

                while (player.life > 0) and (hero.life > 0):
                    output += "\n" + "Round " + str(round)
                    print("Round " + str(round))
                    print("# Round " + str(round) + " # ")
                    print("# PV de " + hero.nom + " " + str(hero.life))
                    output += "\n" + "# PV de " + hero.nom + " " + str(hero.life)
                    print("# PV de " + player.nom + " " + str(player.life))
                    output += "\n" + "# PV de " + player.nom + " " + str(player.life)

                    if player.initiative() > hero.initiative():
                        output += "\n" + player.nom + " begin"
                        print(player.nom + " begin")
                        tmpDegats = player.damages()
                        hero.defense(tmpDegats)
                        output += "\n" + player.nom + " degats " + str(tmpDegats)
                        print(player.nom + " degats " + str(tmpDegats))

                        if hero.life <= 0:
                            output += "\n" + player.nom + " win"
                            print(player.nom + " win")
                            break  # Exit the inner loop if hero dies
                        else:
                            tmpDegats = hero.damages()
                            player.defense(tmpDegats)
                            output += "\n" + hero.nom + " degats " + str(tmpDegats)
                            print(hero.nom + " degats " + str(tmpDegats))
                    else:
                        output += "\n" + hero.nom + " begin"
                        print(hero.nom + " begin")
                        tmpDegats = hero.damages()
                        player.defense(tmpDegats)
                        output += "\n" + hero.nom + " degats " + str(tmpDegats)
                        print(hero.nom + " degats " + str(tmpDegats))

                        if player.life <= 0:
                            output += "\n" + hero.nom + " win"
                            print(hero.nom + " win")
                            break  # Exit the inner loop if player dies
                        else:
                            tmpDegats = player.damages()
                            hero.defense(tmpDegats)
                            output += "\n" + player.nom + " degats " + str(tmpDegats)
                            print(player.nom + " degats " + str(tmpDegats))

                    round += 1

                # If hero dies during any fight, stop the entire quest
                if hero.life <= 0:
                    output += "\n" + "You loose"
                    print("You loose")
                    return output

            # If hero survives all fights
            output += "\n" + hero.nom + " win"
            print(hero.nom + " win")
            hero.setXP(10 * len(self._lAvatar) * self._lvl)
            hero.bag.addItem(self._itemGift)
        return output

    def __str__(self):
        return self._itemGift


class Hero(Avatar):
    def __init__(self, targs):
        Avatar.__init__(self, targs)
        self._xp = 1
        self._profession = targs['profession']
        self._lvl = self.lvl()

    def lvl(self):
        lvl = math.floor(self._xp / 100)
        if lvl < 1:
            lvl = 1
        if lvl > self._lvl:
            print("### new level ###")
            self.newLvl()
        return lvl

    def newLvl(self):
        for i in self._stat.__dict__:
            self._stat.__dict__[i] += 5
        self._life = self._stat.life_point
        print("### stats upgrade ###")

    def setXP(self, xp):
        self._xp += xp
        self._lvl = self.lvl()

    @property
    def __str__(self):
        output = "joueur " + self._nom + " de niveau " + str(self._lvl) + " classe " + str(
            self._classe) + " race " + str(self._race)
        return output

    def save(self):
        fileName = str(date.today()) + "_" + str(Hero.id) + "_" + str(self._nom) + ".txt"
        f = open(fileName, "w+")
        f.write(self._nom + "\n")
        f.write(self._race.name + "\n")
        f.write(self._classe.name + "\n")
        f.write("lvl: " + str(self._lvl) + "\n")
        f.write("xp: " + str(self._xp) + "\n")
        for i in self._stat.__dict__:
            output = str(i) + " " + str(self._stat.__dict__[i])
            f.write(output + "\n")
        for i in self._equipment:
            f.write(str(i) + "\n")
        for i in self.getBag():
            f.write(str(i) + "\n")
        f.close()

    def saveXML(self):
        fileName = str(date.today()) + "_" + str(Hero.id) + "_" + str(self._nom) + ".xml"
        f = open(fileName, "w+")
        xml = "<?xml version='1.0' encoding='UTF-8'?>"
        xml += "<avatar id='" + str(Hero.id) + "'>"
        xml += "<name>" + self._nom + "</name>"
        xml += "<race>" + self._race.name + "</race>"
        xml += "<level>" + self._classe.name + "</level>"
        xml += "<xp>" + str(self._lvl) + "</xp>"
        xml += "<name>" + str(self._xp) + "</name>"
        xml += "<stats>"
        for i in self._stat.__dict__:
            xml += "<" + str(i) + ">" + str(self._stat.__dict__[i]) + "</" + str(i) + ">"
        xml += "</stats>"
        xml += "<equipments>"
        it = 1
        for i in self._equipment:
            xml += "<item_" + str(it) + ">" + i.name + "</item_" + str(it) + ">"
            it += 1
        xml += "</equipments>"
        xml += "<bag>"
        it = 1
        for i in self.getBag():
            xml += "<item_" + str(it) + ">" + i.name + "</item_" + str(it) + ">"
            it += 1
        xml += "</bag>"
        xml += "</avatar>"
        f.write(xml)
        f.close()

    @staticmethod
    def load():
        pass


class Tableau:
    def __init__(self, hero, length=20):
        """
        Initiale the tableau game mode
        :param hero: The hero playing the game
        :param length: Length of the tableau (default 20)
        """
        self._hero = hero
        self._length = length
        self._board = self._generate_board()
        self._current_position = 0

    def _generate_board(self):
        """
        Generate a board with random elements
        Possible elements:
        - None (empty space)
        - Item
        - Enemy
        """
        board = []
        for _ in range(self._length):
            element_type = random.choices(
                ['empty', 'item', 'enemy'],
                weights=[0.5, 0.25, 0.25]
            )[0]

            if element_type == 'empty':
                board.append(None)
            elif element_type == 'item':
                # Generate a random item from hero's possible items
                possible_items = [Potion]  # Add more item types as needed
                board.append(random.choice(possible_items))
            elif element_type == 'enemy':
                # Generate a random enemy
                enemy_races = [orc, dwarf]
                enemy_classes = [warrior, wizard]
                enemy = Mobs({
                    'name': f'Enemy at pos {len(board)}',
                    'race': random.choice(enemy_races),
                    'classe': random.choice(enemy_classes),
                    'bag': Bag({"sizeMax": 10, "items": []}),
                    'equipment': [sword],  # Default equipment
                    'element': 'Fire',
                    'type': 'random'
                })
                board.append(enemy)

        return board

    def roll_dice(self):
        """
        Roll a dice to determine movement
        """
        return random.randint(1, 6)

    def play_turn(self):
        """
        Play a single turn in the tableau
        Returns output of the turn
        """
        output = ""
        dice_roll = self.roll_dice()
        output += f"{self._hero.nom} rolls {dice_roll}\n"

        # Move hero
        self._current_position += dice_roll
        output += f"{self._hero.nom} moves to position {self._current_position}\n"

        # Check if hero has gone past the board
        if self._current_position >= self._length:
            output += f"{self._hero.nom} completed the tableau!\n"
            self._hero.setXP(100)  # Reward XP for completing the tableau
            return output

        # Check current board element
        current_element = self._board[self._current_position]

        if current_element is None:
            output += "Nothing happened. The space is empty.\n"
        elif isinstance(current_element, Item):
            output += f"{self._hero.nom} found an item: {current_element.name}\n"
            self._hero.bag.addItem(current_element)
            self._board[self._current_position] = None  # Remove item after picking up
        elif isinstance(current_element, Mobs):
            output += f"Enemy encountered: {current_element.nom}\n"
            quest = Quest({'lAvatar': [current_element], 'lvl': 1, 'gift': sword})
            battle_result = quest.run(self._hero)
            output += battle_result

        return output

    def play_game(self):
        """
        Play the entire tableau game
        """
        output = f"Starting Tableau Game with {self._hero.nom}\n"

        while self._current_position < self._length:
            turn_output = self.play_turn()
            output += turn_output

            # Check if hero died during the game
            if self._hero.life <= 0:
                output += f"{self._hero.nom} died. Game Over!\n"
                break

        if self._current_position >= self._length:
            output += f"{self._hero.nom} completed the tableau and gained experience!\n"

        return output

    ### RACE


statElfe = Stat({'strength': 5, 'magic': 10, 'agility': 10, 'speed': 5, 'charisma': 5, 'chance': 5})
elfe = Race('Elfe', statElfe)
statHuman = Stat({'strength': 10, 'magic': 10, 'agility': 5, 'speed': 5, 'charisma': 5, 'chance': 5})
human = Race('Human', statHuman)
statDwarf = Stat({'strength': 10, 'magic': 0, 'agility': 10, 'speed': 5, 'charisma': 5, 'chance': 10})
dwarf = Race('Dwarf', statDwarf)
statOrc = Stat({'strength': 15, 'magic': 0, 'agility': 5, 'speed': 10, 'charisma': 5, 'chance': 5})
orc = Race('Orc', statOrc)
### CLASS
statWizard = Stat({'strength': 0, 'magic': 10, 'agility': 0, 'speed': 0, 'charisma': 10, 'chance': 10})
wizard = Race('Wizard', statWizard)
statWarrior = Stat({'strength': 10, 'magic': 0, 'agility': 5, 'speed': 5, 'charisma': 5, 'chance': 5})
warrior = Race('Warrior', statWarrior)
### ITEMS
statSword = Stat({'strength': 5, 'magic': 0, 'agility': 5, 'speed': 5, 'charisma': 0, 'chance': 5})
sword = Equipment({'classList': 'warrior', 'place': 'hand', 'name': 'dragon sword', 'type': 'sword', 'space': 2, },
                  statSword)
statBaton = Stat({'strength': 0, 'magic': 10, 'agility': 0, 'speed': 5, 'charisma': 0, 'chance': 5})
baton = Equipment({'classList': 'wizard', 'place': 'hand', 'name': 'wizard baton', 'type': 'baton', 'space': 2, },
                  statBaton)
statPotion = Stat({'strength': 0, 'magic': 0, 'agility': 0, 'speed': 0, 'charisma': 0, 'chance': 0})
Potion = Item({'name': 'life potion', 'type': 'potion', 'space': 2, }, statPotion)
### BAG
myBag = Bag({"sizeMax": 20, "items": [Potion, Potion]})
### MOBS
mechant1 = Mobs(
    {'name': 'orc 1', 'race': orc, 'classe': warrior, 'bag': myBag, 'equipment': [sword], 'element': 'Fire',
     'type': 'soldier'})
mechant2 = Mobs(
    {'name': 'orc 2', 'race': orc, 'classe': warrior, 'bag': myBag, 'equipment': [sword], 'element': 'Fire',
     'type': 'soldier'})


def main():
    hero1 = Hero(
        {'name': 'Jean', 'race': human, 'classe': warrior, 'bag': myBag, 'equipment': [sword], 'element': 'Fire',
         'profession': 'chomeur'})
    hero2 = Hero(
        {'name': 'Pierre', 'race': elfe, 'classe': wizard, 'bag': myBag, 'equipment': [baton], 'element': 'Fire',
         'profession': 'chomeur'})
    hero1.save()
    hero1.saveXML()
    hero2.save()
    hero2.saveXML()
    ### QUEST
    firstQuest = Quest({'lAvatar': [mechant1, mechant2], 'lvl': 2, 'gift': sword})
    # firstQuest = Quest({'lAvatar': [hero2], 'lvl': 2, 'gift': sword})
    # firstQuest.run(hero1)
    tableau_game = Tableau(hero1)
    game_result = tableau_game.play_game()
    print(game_result)


if __name__ == "__main__":
    # execute only if run as a script
    main()
