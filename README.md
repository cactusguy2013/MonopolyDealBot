# MonopolyDealBot

If you wanted to try this bot I don't host it on a server anywhere so you would have to create you own bot (Which is real easy) and change the bottom line of MonpolyDealBot.py, and where it says REMOVED replace it with your own bot authentication key and run the code. The code also does not automatically add the colour emojis so you have to add those to the discord server yourself.

## How to play:
First of all the bot doesn't enforce many rules it is up to the players to enforce them, kind of like the game *Tabletop Simulator*. This section also doesn't describe how to play the original game but how to use the bot commands in order to play the game.

* Have every player type !join
* Once everyone had done that someone has to write !start
* The bot will automatically draw cards and dm the players their hand
* You can find out the necessary arguements to a command by typing !commands but order of arguments doesn't matter
* On your turn you may want to !place a property on the table
* You may want to !bank a money or action card
* You may want to !play an action card
* If you want to one of your cards to be moved from one set to another use !move
* When you are charged money you can !pay @user money_amounts (eg *!play @monopoly_player 2 2 3* will pay that user two $2M's and a $3M value card from your bank if you have them)
* When an action card allows you to take someones card use !take
* When a action card requires you to give someone a card use !give
* When you use *Deal Breaker* you will want to use !take_set
* Before you end your turn if you have more than 7 cards you will want to use !discard
* To end your turn use !end
* !name will change the name given to you in the game (by default it's you display name, which can be your server nickname)

I would recommend using !join and !start in the channel you are playing the game in but then write all the other commands in the dm with Monopoly Deal Bot, it's easier and it keeps the channel cleaner. This does however mean you cannot @ a user but you can instead write their display name in place of the @ mention and it will work the same. Sometimes a user's display name will have symbols that cannot be typed or are just annoyingly long to type out, in which you can ask that user to use !name *new_name* to rename themselves in the game
