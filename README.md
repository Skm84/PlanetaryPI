Welcome to the source code of my interplanetary date-time conversion API, the first half of this document is explaining the way the api works and some basic decisions i made while programming the API. The second half of this document will be documentation for the api, json formatting of inputs and outputs along with the URL and other important information needed for programming. please note that if you are calling the API for the first time, it may take roughly 50-60 seconds to recieve a response due to the hosting platform shutting itself down every 60 seconds.

Context:
Our code was originally made as a part of the Nasa Hunch Hackathon as a response to the cosmic calendar program. The problem is essentially trying to create a conversion tool for date and time between planets and other celestial bodies.

Our solution created a program that takes a date, a time and timezone (or longitude for celestial bodies that arent earth) on one planet, and then converts it into a date and time on another planet, while also adjusting for a timezone on that planet. Currently we have implemented, conversions between Earth, Mars, Saturn and Phobos but more celestial bodies are on the way.

How it works:
The code works by setting a reference date on each planet, for earth thats 01/01/2025 at 00:00:00 UTC, which was 1:04:03 01/0 on mars, there is functionality coming that allows each user to change these reference date but its not recommened due to the fact that changing one reference date, means youll need to change the other reference dates in order to keep the program accurate. The main algorithm works by first taking the following inputs: the planet you want to convert from, the planet you want to convert to, the timezone/longitude on the planet you want to convert from (-180,180), the timezone/longitude of the planet you want to convert to (-180,180), the date on the planet you want to convert from, the time on the planet you want to convert from. It then takes takes the date and time and adjusts for longitude by adding or taking away time from the date, essentially adjusting the time back to what it would be at longitude 0 on that planet, it then finds the time elapsed between the day/time and the reference date for that planet. It takes the number of seconds elapsed and adjusts for timezone on the new planet by adding or subtracting a number of seconds based on longitude. After this it does multiple divisions to convert the elapsed seconds back into a date and a time.

Formatting:
Because dates arent defined on other planets, we have decided to take a standard notation of Sols/Years, Sols refers to the number of solar days that have passed since the year started, and years refers to the number of full years elapsed since the reference date. Our time Works on the same format of hour:minute:seconds but for each planet the number of hours in a day have changed and the number of minutes in an hour have changed, for example mars has a 24 hour day, but it has a roughly 62 minute hour, in contrast on saturn each day is only 10 hours but each hour is 63 minutes. This is done so that humans have an easier time adjusting to the planetary times.

Documentation:
When you pass a request into the api, it should provide the following JSON keys:
      - from_planet (e.g., "Earth", "Mars", "Phobos", "Saturn")
      - to_planet (a string or a list; if string, comma-separated values are accepted)
      - date (for Earth, "dd/mm/yyyy"; for Mars: "year/sol"; for Phobos/Saturn: "year/day")
      - time ("HH:MM:SS", 24-hour format)
      - from_earth_timezone (if applicable, default "UTC")
      - to_earth_timezone (if applicable, default "UTC")
      - from_planetary_longitude (if applicable)
      - to_planetary_longitude (if applicable)



Contact:
Feel free to contact me at 972 439 0650 or email me at 18SaiSathanapalli@gmail.com. If you think of any other interesting features or planets that youd like me to add to the api, dont hesitate to reach out and please dont hesitate to reach out if you have a project that you think i could help with, im always looking to learn and get more experience regardless of what the project is.
