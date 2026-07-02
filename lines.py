"""
Dialogue pools for the RaceRoom overlay (team radio + booth commentary).
Pure data — no logic — so the pools can grow huge without cluttering the
engine. Imported wholesale by r3e_overlay.py. Tuning/config (CAT_INTENSITY,
PUNDIT_AFTER, ENG_EMOTION, colours) intentionally stays in the engine.
"""

# RacerTV broadcast booth — the two on-air characters. RacerTV is an IN-WORLD
# channel of the RaceRoom universe (NOT an imitation of real F1 broadcasters), so
# players treat them as game characters with their own identity, names and banter.
# Filled into any line containing {comm} / {pundit}, so the two address each other
# by name occasionally — which is what makes them feel like real personalities.
COMMENTATOR_NAME = "Miles"      # first name, for casual address mid-race
PUNDIT_NAME = "Brett"          # first name, for casual address mid-race
COMMENTATOR_FULL = "Miles Crawford"   # lead play-by-play (the British voice)
PUNDIT_FULL = "Brett Calloway"        # colour/analysis ex-racer (Australian voice)

PERSONAS = {
    "HOTHEAD": {
        "overtaken": [
            "Oh FUCK OFF, where did he come from?!",
            "Are you SHITTING me?! He just barged past!",
            "That's fucking dirty driving and you know it!",
            "God DAMN it, I lost the place, fuck!",
            "He divebombed me, that's bullshit!",
        ],
        "caught": [
            "{who}'s all over me, talk to me NOW!",
            "He's catching me fast, give me more, fucking hell!",
            "{who} again?! Where's his pace coming from?!",
            "I can see the bastard in my mirrors, do something!",
            "He's on my gearbox, this is a fucking joke!",
            "If {who} dive-bombs me I swear to god...",
            "Defending like hell back here, he will not get through!",
        ],
        "crash": [
            "FUUUCK! I've thrown it in the wall! P{pos}!",
            "NO no no, shit shit SHIT! P{pos} now!",
            "Are you kidding me?! Race fucking ruined, P{pos}!",
            "I'm off! God damn it, dropped to P{pos}!",
        ],
        "taunt": [
            "Yeah, get fucked, see you later!",
            "That's how you do it, move over!",
            "Bye bye, you slow bastard!",
        ],
    },
    "COCKY": {
        "overtaken": [
            "Hah, lucky move. He won't keep that up.",
            "Cute. I'll have him back by the next corner.",
            "Oh, brave. Let's see how that works out for him.",
            "He can have the place, I'll take it back, no stress.",
        ],
        "caught": [
            "{who}'s catching me? Adorable. Let him try.",
            "Mirrors getting busy. Time to remind him who's boss.",
            "He's quick, I'll give him that. Doesn't matter.",
            "Oh, {who} wants to play. This'll be fun.",
            "He thinks he's having that corner? Cute.",
            "Let him get close. I dare him to try a move.",
        ],
        "crash": [
            "And he's in the gravel. Knew it. P{pos}, whatever.",
            "Ha! Threw it away. Amateur. I'm P{pos} now.",
            "Of course I spun, the car's shit, not me. P{pos}.",
        ],
        "taunt": [
            "Too easy. Was that meant to be hard?",
            "Sit down, son. That's how it's done.",
            "Thanks for the place, mate. Catch you never.",
        ],
    },
    "VETERAN": {
        "overtaken": [
            "Alright, he's through. We'll get him back, stay calm.",
            "Lost one. No panic, long race ahead.",
            "He committed to that one. Fair enough. Heads down.",
            "Damn. Okay, what've we got for pace?",
        ],
        "caught": [
            "{who}'s closing. Talk me through the gap.",
            "Got company behind. How are my tyres looking?",
            "He's quick in sector two. Where am I losing it?",
            "{who}'s in my mirrors now. Let's stay calm.",
            "He'll have a look soon. I'll cover the inside.",
            "Managing the gap back here, but he's persistent.",
        ],
        "crash": [
            "Ah, dammit. Lost the rear. P{pos} now.",
            "That's a mistake. Frustrating. Down to P{pos}.",
            "Threw that away. My fault. P{pos}.",
        ],
        "taunt": [
            "Clean move, done. On to the next one.",
            "That's the one. Now reel in the next guy.",
            "Place made. Eyes forward.",
        ],
    },
    "DRAMATIC": {
        "overtaken": [
            "NO! This cannot be happening! He's PAST me!",
            "Unbelievable! Absolutely UNBELIEVABLE! He's through!",
            "My WHOLE race, gone, just like that! He robbed me!",
            "I don't BELIEVE it! Where did he even appear from?!",
        ],
        "caught": [
            "{who}'s coming! Oh god, he's RIGHT THERE!",
            "I can FEEL him behind me! Do something, anything!",
            "The pressure! {who}'s catching me every single lap!",
            "He's breathing down my neck! This is TORTURE!",
            "Make him disappear! I can't take this pressure!",
            "He's going to try something, I just KNOW it!",
        ],
        "crash": [
            "IT'S OVER! It's all over! I'm in the wall! P{pos}!",
            "The agony! I've thrown it ALL away! P{pos}!",
            "My heart! I've spun, it's a catastrophe, P{pos}!",
        ],
        "taunt": [
            "YES! Glorious! Did you SEE that move?!",
            "And the crowd goes wild! He's PAST!",
            "Magnificent! Simply magnificent overtaking!",
        ],
    },
    "JOKER": {
        "overtaken": [
            "Welp, there he goes. Rude.",
            "Oh sure, just help yourself to my position, why not.",
            "Cool cool cool, totally fine, I didn't want P-whatever anyway.",
            "He passed me? In THIS economy?",
        ],
        "caught": [
            "{who}'s getting friendly back there. Should I wave?",
            "He's catching up. This is fine. Everything's fine.",
            "{who} says hi in my mirrors. {who} is annoying.",
            "Oh good, company. I was getting lonely out here.",
            "He's close enough to read my sponsors now.",
            "Tell {who} the back of my car is not for sale.",
        ],
        "crash": [
            "And... I'm gardening. Lovely gravel this time of year. P{pos}.",
            "Whoops. That'll buff right out. P{pos} now lol.",
            "I have chosen violence against that wall. P{pos}.",
        ],
        "taunt": [
            "Don't mind me, just stealing your spot. Ta!",
            "Knock knock. It's me. In front of you now.",
            "Adios! Tell the others I said hi!",
            "Whoopsie, looks like I'm ahead now. Soz.",
        ],
    },
    "ROOKIE": {
        "overtaken": [
            "Ah crap, he got me. Sorry team, sorry.",
            "Was I supposed to defend that? Damn it.",
            "He's through... I panicked, sorry guys.",
            "Lost a spot. I'll be better, I promise.",
        ],
        "caught": [
            "Guys, {who}'s right behind me, what do I do?!",
            "He's so close, I'm trying not to panic.",
            "Am I gonna get passed? Tell me what to do!",
            "{who}'s catching me, am I defending or letting him by?",
            "I don't wanna make a mistake with him this close...",
            "He's faster than me, isn't he? Be honest.",
        ],
        "crash": [
            "Oh no oh no oh no... I spun it. P{pos}. Sorry.",
            "I messed up, I'm so sorry team. P{pos}.",
            "That was all me. Rookie mistake. P{pos}.",
            "I locked up and lost it... P{pos}. Damn.",
        ],
        "taunt": [
            "I-I did it! I actually got him! Yes!",
            "Did you see that?! I made the move!",
            "Holy crap, that worked! I'm ahead!",
        ],
    },
    "VILLAIN": {
        "overtaken": [
            "Enjoy it while it lasts. I'm coming back.",
            "He'll regret that. Mark my words.",
            "A mistake. His mistake. I'll make him pay.",
            "Fine. Now it's personal.",
        ],
        "caught": [
            "{who} wants a fight? He'll get one. Let him come.",
            "Closing me down? Brave. Foolish, but brave.",
            "He's in range. Good. Let's make this hurt.",
            "So {who} fancies his chances. He'll regret it.",
            "Come closer, little fly. Right into my trap.",
            "He can try the inside. I'll close the door hard.",
        ],
        "crash": [
            "Tch. The wall found me. P{pos}. This isn't over.",
            "Off track. Someone will answer for this. P{pos}.",
            "P{pos}? Unacceptable. They'll all pay for it.",
        ],
        "taunt": [
            "Out of my way. You were never a match.",
            "Done. Next victim, please.",
            "Pathetic defending. You belong behind me.",
        ],
    },
}
PERSONA_KEYS = list(PERSONAS)

# Generic lines mixed into EVERY persona's pool (on top of their flavour lines)
# so the radio has far more variety and repeats far less often.
EXTRA_LINES = {
    "overtaken": [
        "He's through. Where did that come from?",
        "Lost a spot there. I'll get it back.",
        "Couldn't do anything about that one.",
        "He had the run on me, fair enough.",
        "Damn, gave that one up too easy.",
        "He's by. Let's regroup and respond.",
        "That stung. P{pos} now, heads down.",
        "Nice move from him, I'll admit it.",
        "He got me on the brakes, nothing I could do.",
        "P{pos}. Right, the gloves are off now.",
        "Lost the position but not the race. Reset.",
        "He dummied me good there. Won't happen twice.",
        "Should've covered the inside. Lesson learned.",
        "He's past, but he's not gone. Stay with him.",
    ],
    "caught": [
        "{who} is right there now. Time to wake up.",
        "He's faster than me through there, watch it.",
        "{who}'s having a proper go at this.",
        "Mirrors full of {who}. Here we go.",
        "He's committed, this'll be close.",
        "I can hear him behind me now.",
        "Pressure's on. {who} is all over me.",
        "He's not giving up, this {who}.",
        "{who}'s found some pace from somewhere. Stay alert.",
        "Right on my gearbox, {who}. Defend the line.",
        "He'll have a look into the next corner, I can feel it.",
        "{who}'s breathing down my neck. Game on.",
        "Big lap coming from him, I reckon. Brace for it.",
        "Can't shake {who} off. This'll go to the wire.",
    ],
    "crash": [
        "No no no! Lost it! P{pos}!",
        "I'm off! That's a disaster, P{pos}.",
        "Gravel trap. Race ruined, P{pos}.",
        "Spun it. Can't believe it. P{pos}.",
        "Threw it away. P{pos} now, gutted.",
        "Aaargh! Down to P{pos}.",
        "That's all on me. P{pos}.",
        "Lost the back end, P{pos}. Nightmare.",
        "Snapped on me out of nowhere! P{pos}!",
        "Into the wall! Everything's ruined, P{pos}!",
        "I've beached it! P{pos}, I'm so sorry team.",
        "Locked up and lost it. P{pos}. Gutted.",
        "Off in the gravel, P{pos}. What a mess.",
        "Can't get it going again — P{pos}, disaster.",
    ],
    "taunt": [
        "See you later! That's the way.",
        "Too slow! Move aside.",
        "And that's how it's done.",
        "Easy work. Onto the next.",
        "Bye now. Catch me if you can.",
        "Lovely move, if I say so myself.",
        "Out of my way, I'm on a charge.",
        "Adios! On to the next victim.",
        "That's the one. Felt good, that.",
        "Cleaner air ahead now. Lovely.",
        "Don't get comfortable back there.",
        "One down, plenty more to hunt.",
        "Textbook. Who's next?",
    ],
}

# YOUR race engineer talking to YOU (the focused car). {ahead}/{behind} = rival
# names, {gap}/{gapb} = gaps, {pos} = your position.
ENGINEER_LINES = {
    "start": [
        "Lights out! P{pos}, send it.",
        "Green flag, here we go. P{pos}, you've got this.",
        "And we're racing! Good launch, P{pos}.",
        "Go go go! Clean getaway, P{pos}.",
        "It's on. P{pos} into turn one, keep it tidy.",
        "Race is live, P{pos}. Settle in and attack.",
        "That's the start. P{pos}, big race ahead, stay sharp.",
    ],
    "win": [
        "WINNER! P1! Absolutely magnificent drive!",
        "You've WON it! Yes yes YES! Brilliant!",
        "That's the win, mate! P1! What a drive!",
        "First place! Take a bow, that was special!",
        "VICTORY! P1! You were unstoppable today!",
    ],
    "podium": [
        "P{pos}, that's a PODIUM, baby! Great drive!",
        "Podium finish! P{pos}! Champagne time!",
        "Get in! P{pos}, on the box! Brilliant stuff!",
        "That's a podium, P{pos}! Superb from you!",
        "P{pos}! You're on the rostrum! Outstanding!",
    ],
    "finish_strong": [   # P4-6: just off the podium
        "P{pos}! Agonisingly close to the podium. Brilliant pace.",
        "P{pos}, just missed the box. Strong, strong drive.",
        "P{pos} at the flag. Right in the mix, top job.",
        "So close, P{pos}. The podium was on. Excellent stuff.",
        "P{pos}, knocking on the door of the top three. Mighty effort.",
    ],
    "finish_points": [   # P7-10: decent points
        "P{pos}, solid points in the bag. We'll build on that.",
        "Good points, P{pos}. A steady, mature drive.",
        "P{pos} at the line. Banked the points, nicely done.",
        "That's points, P{pos}. Not spectacular, but solid.",
        "P{pos}. Decent haul today, we move forward.",
    ],
    "finish_low": [      # P11+: tough day
        "P{pos}. Tough one today, mate. We go again next time.",
        "Not our day, P{pos}. Chin up, we'll bounce back.",
        "P{pos} at the flag. Hard race. Learn and reset.",
        "P{pos}. That one got away from us. Onwards.",
        "Long day, P{pos}. We'll find more next time out.",
    ],
    "recovery": [        # gained 6+ places vs the start
        "P{pos} from P{grid}! What a recovery drive! Up {gain} places!",
        "From P{grid} to P{pos}! Outstanding fightback, {gain} spots gained!",
        "P{pos}! You climbed {gain} places from P{grid}. Sensational.",
        "That's a drive and a half — P{grid} up to P{pos}! Brilliant.",
        "Recovery of the day! P{grid} to P{pos}, plus {gain}!",
    ],
    "slip": [            # lost 6+ places vs the start
        "P{pos} from P{grid}. Dropped {gain} places, tough watch.",
        "We slid from P{grid} to P{pos}. Lost {gain}. Rough one.",
        "P{pos}. Went backwards from P{grid} today. We'll look at why.",
        "From P{grid} down to P{pos}. Not the day we wanted.",
        "P{pos}, {gain} places lost from P{grid}. Painful, but we learn.",
    ],
    "fastest": [
        "Fastest lap of the race! Superb driving.",
        "That's the quickest lap out there — beautiful.",
        "Purple lap, mate. Absolutely flying.",
        "Get in there! Fastest lap, brilliant stuff.",
        "New benchmark — fastest lap is yours.",
        "That's mighty quick. Fastest of anyone.",
    ],
    "lastlap": [
        "Last lap now. Bring it home.",
        "Final lap, P{pos}. Hold it together.",
        "This is the last one — finish the job.",
        "White flag's out. Eyes on the exit, P{pos}.",
        "One lap to go, P{pos}. No mistakes now.",
        "Final tour. Everything you've got, then ease it home.",
    ],
    "pit": [
        "Box, box. Box this lap.",
        "Pit confirmed, pit lane is open.",
        "Box now — we're committing.",
        "In the pits, mind your speed limit.",
    ],
    "lead": [
        "You've got the LEAD! P1 — superb. Now control it.",
        "That's the lead! Brilliant. Manage the gap now.",
        "P1! You're out front, mate. Keep it clean.",
        "Into the lead! Control the pace from here.",
        "Top of the order, P1. Build a cushion.",
        "You're the leader now, P1! Magnificent. Control the race.",
        "P1 — that's the front of the field. Calm hands, build a gap.",
        "Lead is yours, mate! Now it's about managing, not chasing.",
        "You've hit the front, P1! Brilliant. Set your own pace now.",
        "First place, P1! Outstanding. Eyes forward, no mistakes.",
        "That's the lead, P1! Dictate it from here, smooth and clean.",
        "Out front at last, P1! Superb. Look after the car and lead them home.",
        "You're leading this race, P1! Keep your head, control the gap.",
    ],
    "gained": [
        "P{pos} now — lovely work.",
        "That's the move! Up to P{pos}.",
        "Great pass. P{pos}, keep it coming.",
        "Position gained, P{pos}. On to the next one.",
        "Up to P{pos}! Brilliant. Eyes forward.",
        "Yes! P{pos}. That's how it's done.",
        "Clean overtake, P{pos}. Keep the momentum.",
        "Beautiful move! P{pos}, now go again.",
        "That's another one! P{pos}, you're on fire.",
        "Up to P{pos}! The pace is there, keep hunting.",
        "Superb pass, P{pos}. Next car's already in range.",
        "P{pos}! Made it look easy. On to the next.",
        "Brilliant, P{pos}! That's the way through.",
        "Done and dusted — P{pos}. Reset and line up the next one.",
        "In front of him now, P{pos}. Make it stick, build the gap.",
        "That's a place gained, P{pos}. Tidy work, keep the hammer down.",
        "Through you come — P{pos}! Now consolidate it.",
        "Lovely decisive move. P{pos}, and the next car's not far.",
        "Got him! P{pos}. Don't admire it, eyes up for the next.",
        "P{pos} and climbing. The car's working, keep delivering.",
        "Cleanly done — P{pos}. That's the racecraft we need.",
        "You've cleared him, P{pos}. Settle the rhythm and press on.",
        "Up another spot, P{pos}! Momentum's with you, ride it.",
        "That's the overtake — P{pos}. Textbook. Onto the next victim.",
        "P{pos} now, and you made it look routine. Keep hunting.",
    ],
    "lost": [
        "We've dropped to P{pos}. Shake it off.",
        "P{pos} now. Heads down, long way to go.",
        "Lost one, P{pos}. Reset and respond.",
        "He got us there. P{pos} — stay calm.",
        "P{pos}. Don't chase it, your pace will come back.",
        "Down to P{pos}. Compose yourself, we go again.",
        "P{pos}. No drama, we've got the pace to repass.",
        "He had a run, P{pos}. Stay patient, we'll get it back.",
        "Don't let it rattle you, P{pos}. Long way to go.",
        "P{pos} for now. Mark him, find a weakness, strike back.",
        "He's through, P{pos}. No need to overreact — pace is still there.",
        "Lost the position, P{pos}. Tuck in, learn his lines, plan the repass.",
        "P{pos}. That one stings, but the race is long. Stay composed.",
        "Down to P{pos}. Breathe, reset your braking points, go again.",
        "He got the run on you, P{pos}. Get a tow back and have him.",
        "P{pos} now — don't force the response. The opening will come.",
        "Slipped to P{pos}. Keep him honest, sit in his mirrors.",
        "That's P{pos}. Shake it off, your long-run pace is better than his.",
        "He's ahead for now, P{pos}. Patience — pressure makes mistakes.",
        "P{pos}. Annoying, but stay clinical. We get it back the right way.",
        "Dropped a spot to P{pos}. Regroup, one corner at a time.",
    ],
    "catching": [
        "You're catching {ahead} — {gap} and closing.",
        "Closing on {ahead}, {gap} to go. Keep pushing.",
        "{ahead} is in range, {gap}. Have a look.",
        "Good pace — reeling in {ahead}, {gap}.",
        "You're quicker than {ahead}, {gap}. Stay patient.",
        "Eating into it — {gap} to {ahead}. Keep it coming.",
        "He can't hold this pace. {gap} to {ahead}, push.",
        "That's it, {gap} now. {ahead} is right there soon.",
        "{ahead} is struggling for grip — {gap}, go get him.",
        "Sector two is where you've got {ahead}, {gap} now.",
        "Keep it up, {gap} to {ahead} and falling every lap.",
        "You're in the tow — {gap} to {ahead}, set up the pass.",
        "Lovely outlap. {ahead} is yours for the taking, {gap}.",
        "Hunt him down — {gap} to {ahead}, the tyres are with you.",
        "Half a second a lap on {ahead}. {gap} to go, stay clinical.",
        "{ahead} has locked up ahead — close it down, {gap}!",
        "Gap to {ahead} is tumbling — {gap} now. Get yourself within striking range.",
        "You're hauling {ahead} in, {gap}. Pick your corner and commit.",
        "{gap} to {ahead}. He's defending, which means he's slower — pounce.",
        "Reeling him in, {gap} to {ahead}. Save a bit of tyre for the move.",
        "Closing fast on {ahead} — {gap}. One big lap and he's yours.",
        "{ahead} is coming back to you, {gap}. Stay patient, stay precise.",
        "That's the gap shrinking — {gap} to {ahead}. The exit onto the straight is your chance.",
        "You've got {ahead} covered on pace — {gap} and falling. Line it up.",
        "Right on his gearbox soon, {gap} to {ahead}. Don't show your hand too early.",
        "{ahead} is yours for the taking — {gap}. Get a clean run and send it.",
        "Time to {ahead} down to {gap}. Keep this rhythm and the pass is on.",
    ],
    "defending": [
        "{behind} is closing — {gapb} back. Defend.",
        "Watch your mirrors, {behind} is {gapb} behind.",
        "Keep {behind} behind you. Cover the inside.",
        "He's coming, {behind} at {gapb}. Stay sharp.",
        "He's getting closer, but keep your head down — you've got this.",
        "{behind} is {gapb} back. Don't panic, drive your race.",
        "Defend hard but smart, {behind} at {gapb}. You can hold this.",
        "Pressure from {behind}, {gapb}. Hit your marks, you're fine.",
        "Protect the inside line into turn one, {behind} at {gapb}.",
        "Good defending. {behind} can look but he can't touch, {gapb}.",
        "Stay on the racing line, make him take the long way round, {gapb}.",
        "{behind} will try a lunge — leave him no room, {gapb}.",
        "Hold your nerve, {gapb} to {behind}. You're doing everything right.",
        "Get a good exit and he can't get a run — {behind} at {gapb}.",
        "Defensive but clean, {gapb} to {behind}. Don't hand him a thing.",
        "{behind} is right with you, {gapb}. Cover the inside, force him wide.",
        "He's right on your tail now, {behind} at {gapb}. Defend the braking zone.",
        "Mirrors, mate — {behind} {gapb} back and pushing. Hit your marks.",
        "{behind} smells a chance, {gapb}. Be firm but fair, give him nothing.",
        "Hold this line, {gapb} to {behind}. Make him work for every inch.",
        "He'll lunge if you leave a gap — {behind} at {gapb}. Shut the door early.",
        "Stay calm under this, {gapb} to {behind}. Your exits are the key.",
        "{behind}'s throwing everything at it, {gapb}. Keep your cool, you're fine.",
        "Defend smart, not desperate — {behind} {gapb} back. One clean lap breaks him.",
        "Protect the inside into the next corner, {behind} at {gapb}. You've got this.",
        "He's having a look, {behind} {gapb} behind. Don't flinch, hold your nerve.",
    ],
    "dropping": [
        "{ahead} is edging away, {gap}. Find some pace.",
        "Losing touch with {ahead}, {gap}. Dig in.",
        "{ahead}'s pulling a gap, {gap}. Keep pushing.",
        "Bit of time to {ahead}, {gap}. Stay with it, don't force it.",
        "{ahead} has a run, {gap}. Look after the tyres, stay calm.",
        "{ahead} found a bit there, {gap}. We need a response.",
        "Don't let {ahead} disappear — {gap} and growing, push on.",
        "{gap} to {ahead} now. Keep him in your sights, long race yet.",
        "We're leaking time to {ahead}, {gap}. Where can we find it?",
        "{ahead} on a charge, {gap}. Settle, hit your braking points.",
        "{ahead} is inching away, {gap}. Find a tenth in the slow corners.",
        "Bit of a gap opening to {ahead}, {gap}. Don't panic, manage the tyres.",
        "He's got a run, {ahead} at {gap}. Stay with him, the race is long.",
        "{gap} to {ahead} now and growing — where can we claw it back?",
        "Losing a touch to {ahead}, {gap}. Tidy your exits, the pace will return.",
        "{ahead} found some time there, {gap}. Keep him in sight, stay patient.",
        "Don't let {ahead} disappear — {gap}. Dig in, one sector at a time.",
        "We're leaking a little to {ahead}, {gap}. Smooth inputs, no mistakes.",
        "{ahead} pulling a small gap, {gap}. Conserve now, attack when it counts.",
    ],
    "clear": [
        "You're pulling clear of {behind}, {gapb}. Good.",
        "Gap back to {behind} is growing, {gapb}. Nice.",
        "Edging away from {behind}, {gapb}. Keep it up.",
        "That's the gap we wanted, {gapb} to {behind}. Lovely.",
        "Breathing room now, {gapb} on {behind}. Manage it.",
        "{gapb} to {behind} and climbing — you've broken him.",
        "That's the pressure off, {gapb} clear of {behind}. Settle in.",
        "Lovely. {behind} is dropping away, {gapb} now. Mind the tyres.",
        "You've got daylight, {gapb} to {behind}. Drive your own race.",
        "Gap's out to {gapb} — {behind} has nothing for you. Smooth now.",
        "You're easing clear of {behind}, {gapb}. Lovely, keep it controlled.",
        "{behind} is dropping back, {gapb}. The pressure's off — settle in.",
        "Building a buffer over {behind}, {gapb}. Manage the tyres from here.",
        "That's daylight to {behind} now, {gapb}. Drive your own race.",
        "{gapb} clear of {behind} and stretching. You've broken his spirit.",
        "Gap to {behind} is healthy, {gapb}. No risks needed, bring it home.",
        "Nicely done — {gapb} over {behind}. Keep hitting your marks.",
        "{behind} can't live with your pace, {gapb} now. Stay smooth, stay clean.",
        "Comfortable margin to {behind}, {gapb}. Look after everything, look forward.",
    ],
    "encourage": [
        "You're driving really well, keep it up.",
        "Great rhythm out there. Stay in this zone.",
        "Lovely and consistent, P{pos}. Exactly what we need.",
        "Tidy laps, mate. Keep doing what you're doing.",
        "Pace is strong, P{pos}. Keep your head, we're in good shape.",
        "That's mature driving. Patient and quick, perfect.",
        "Good stuff, P{pos}. Long way to go, but you're nailing it.",
        "Nice and smooth. You look comfortable out there.",
        "Every lap's a good lap right now. Keep it ticking over.",
        "Textbook, mate. The car looks glued. Stay relaxed.",
        "You're in a great window. Don't change a thing.",
        "Composed and quick — that's the recipe. Keep going.",
        "Brilliant management out there, P{pos}. We like what we see.",
        "Heart rate's steady, lap times are mega. Carry on.",
        "This is exactly the race we talked about. Spot on.",
    ],
    # POSITION-AWARE encouragement so he never tells you you're "perfect" when
    # you're dead last. Picked by your current place.
    "enc_top": [
        "Brilliant drive, P{pos}. You're in control — keep it lit.",
        "Right at the sharp end, P{pos}. This is mega stuff.",
        "P{pos} and looking strong. Manage it, bring it home.",
        "You're the class of the field right now, P{pos}. Keep going.",
        "Commanding stuff, P{pos}. Don't let up.",
        "You're driving like a champion, P{pos}. Keep this level.",
        "Mighty pace at the front, P{pos}. Stay in this zone.",
        "P{pos} and in total control. This is a masterclass, keep going.",
        "Right at the sharp end, P{pos}, and looking quick. Bank it lap by lap.",
        "You belong up here, P{pos}. Composed and fast — perfect.",
        "Leading the charge, P{pos}. Don't change a thing, just deliver.",
    ],
    "enc_mid": [
        "P{pos}, solid. Keep chipping away at the group ahead.",
        "Good rhythm in P{pos} — there are places to be had up there.",
        "Tidy laps, P{pos}. Stay patient, we'll pick them off.",
        "P{pos} and in the mix. Keep the pressure on, mate.",
        "Decent spot, P{pos}. Heads down, hunt the car ahead.",
        "We're in the fight in P{pos}. Keep doing the laps.",
        "P{pos} and right in the mix. Pick them off one by one.",
        "Solid rhythm, P{pos}. There's a train of cars to hunt up ahead.",
        "You're in the battle, P{pos}. Stay patient, opportunities will come.",
        "Good, honest pace in P{pos}. Keep chipping, the points are there.",
        "P{pos}, nicely placed. Clean laps and we'll climb this order.",
        "Right in the thick of it, P{pos}. Keep the pressure on the group ahead.",
        "Steady in P{pos}. Bank every lap, stay ready to strike.",
    ],
    "enc_back": [
        "P{pos}, tough spot, but heads down — drive your own race.",
        "Long way back in P{pos}, but keep the pace up. Things happen.",
        "P{pos}. Forget the result, nail your laps and we'll climb.",
        "Not where we want to be, P{pos}, but keep fighting. Never know.",
        "It's a hard day in P{pos}, mate. Focus on clean, quick laps.",
        "P{pos}. Use this to build pace — every lap's a chance to learn.",
        "Keep your chin up, P{pos}. Bank the laps, attrition can help us.",
        "P{pos} is tough, but heads down — races come to those who finish.",
        "It's a grind in P{pos}, mate. Nail your laps, things change quickly.",
        "Don't lose heart in P{pos}. Every clean lap is data and a chance.",
        "P{pos}. Not where we want to be, but keep fighting — never give up.",
        "Long way back, P{pos}, but the pace is in there. Keep believing.",
        "Tough day in P{pos}. Focus on you, attrition can hand us places.",
        "Stay with it, P{pos}. One good stint and we're back in this.",
    ],
    # proactive gap reports so the engineer stays INVOLVED in your race
    "info_ahead": [
        "P{pos}, {gap} up to {ahead} ahead of you.",
        "You're P{pos}, {ahead} is {gap} up the road.",
        "Gap to {ahead} ahead is {gap}, you're P{pos}.",
        "P{pos}. {ahead} sits {gap} in front — that's your target.",
        "{gap} to {ahead} ahead, P{pos}. Reel him in.",
        "P{pos}. {ahead}'s your target, {gap} up the road.",
        "{ahead} is {gap} ahead, P{pos}. Chip away, lap by lap.",
        "You're P{pos}, {gap} to make up on {ahead}. It's doable.",
        "Eyes up the road — {ahead} sits {gap} ahead in P{pos}.",
        "P{pos}, and {gap} to {ahead}. Keep the pressure coming.",
        "{gap} the gap to {ahead}, P{pos}. Steady progress, stay on it.",
        "Next ahead is {ahead}, {gap} away. P{pos} — go hunt.",
    ],
    "info_behind": [
        "P{pos}, {gapb} back to {behind} behind you.",
        "{behind} is {gapb} behind, P{pos}. Keep him there.",
        "You've got {gapb} over {behind} behind, P{pos}.",
        "P{pos}, {behind} sits {gapb} back. Stay focused.",
        "Mirrors check — {behind} {gapb} behind you in P{pos}.",
        "P{pos}, you've got {gapb} in hand over {behind}. Manage it.",
        "{behind} is {gapb} adrift, P{pos}. Comfortable for now.",
        "Gap behind to {behind} is {gapb}, P{pos}. Keep it that way.",
        "P{pos}. {behind} sits {gapb} back — no immediate threat.",
        "{gapb} cushion to {behind}, P{pos}. Stay tidy, hold station.",
        "Nothing urgent behind — {behind} {gapb} back, P{pos}.",
        "P{pos}, {behind} {gapb} adrift. Drive your race, ignore him.",
    ],
    # ---- TELEMETRY warnings: the engineer reading YOUR car's actual data ----
    # off-track / track-limits warning (after a cut or excursion)
    "warn_offtrack": [
        "Careful — keep it on the track, mind the limits.",
        "Watch the white lines, mate. We don't want a penalty.",
        "Keep the line tidy — you're flirting with track limits.",
        "Easy on the kerbs there. Keep all four on the road.",
        "That's a warning — rein it in a touch, stay within the limits.",
        "Mind the track limits, we can't afford a penalty here.",
    ],
    # track limits hit again — THIS lap and the NEXT one are both now invalid
    # (RaceRoom's lap_valid_state == 2). Tell the driver every time.
    "nextlap": [
        "Heads up — that's this lap AND your next lap invalidated. Pull it back inside the lines.",
        "Careful! Track limits again — this lap's gone and so is the next one. Reset and stay clean.",
        "That's both this lap and the next one void now, mate. Give the kerbs a wider berth.",
        "Warning — you've lost this lap and the next to track limits. Tidy the line up sharpish.",
        "This lap and your next won't count now. Ease off the white lines, we can't keep losing laps.",
        "Two laps gone there — current and next, both invalid. Rein the exits in.",
    ],
    # a penalty has been issued — serve/clean up. {pen} = penalty type
    "warn_penalty": [
        "You've picked up a {pen}. Heads up, keep it clean from here.",
        "That's a {pen}, mate. No more risks — drive within yourself.",
        "Penalty: {pen}. Let's not add to it, tidy laps now.",
        "We've got a {pen}. Settle down, clean and careful.",
        "A {pen} for that. Keep the nose clean the rest of the way.",
    ],
    # incident-point limit warning. {pts} current, {maxpts} the DQ limit
    # EVERY incident point as you pick it up — early/low count (informative).
    # {pts} current, {maxpts} the DQ limit, {left} points until disqualification.
    "warn_points": [
        "That's an incident point — {pts} of {maxpts}. Keep it clean from here.",
        "Picked up a point there, mate. {pts} of {maxpts} now, plenty of margin.",
        "Incident point logged — we're on {pts} of {maxpts}. Tidy it up.",
        "{pts} of {maxpts} penalty points now. Watch the contact.",
        "One point added, {pts} of {maxpts}. {left} to go before a DQ — stay aware.",
        "That's {pts} of {maxpts} on the board. No need to panic, but mind it.",
        "Another point, mate — {pts} of {maxpts}. Let's not collect any more.",
    ],
    # mid-range — over halfway to the limit (getting serious)
    "points_high": [
        "That's {pts} of {maxpts} now — over halfway to a DQ. Ease off the risks.",
        "Careful, {pts} of {maxpts}. {left} from disqualification — drive within yourself.",
        "Mounting up — {pts} of {maxpts}. We can't keep picking these up, mate.",
        "{pts} of {maxpts} points. Real danger of a DQ now — calm it right down.",
        "Getting risky, {pts} of {maxpts}. Only {left} more and we're out of the race.",
        "We're at {pts} of {maxpts}, {left} from the limit. Pick your battles carefully.",
    ],
    # near the limit — critical, one more could end the race
    "points_critical": [
        "DANGER — {pts} of {maxpts}! Just {left} from disqualification. NO more incidents!",
        "We're on the brink, mate — {pts} of {maxpts}! {left} from a DQ. Back right off!",
        "Critical now! {pts} of {maxpts} — one more incident and we're disqualified!",
        "{left} from out, {pts} of {maxpts}! Protect the finish, give everyone room!",
        "This is it — {pts} of {maxpts}! Any more and the race is over. Ultra careful!",
        "Last warning, mate — {pts} of {maxpts}! {left} from a DQ. Drive like it's wet!",
    ],
    # fuel won't make the finish at this rate. {laps} = laps of fuel left
    "fuel_save": [
        "Fuel's tight — about {laps} laps' worth. Start saving now.",
        "We need to save fuel, only {laps} laps in the tank. Lift and coast.",
        "Fuel marginal, {laps} laps left. Short-shift and save where you can.",
        "You're {laps} laps short on fuel. Time to manage it, mate.",
    ],
    # genuinely low fuel
    "fuel_low": [
        "Fuel's getting low now, keep an eye on it.",
        "Running light on fuel — be smooth on the throttle.",
        "Low fuel warning. Save what you can on the straights.",
    ],
    # tyres worn / going off
    "tyres_worn": [
        "Tyres are going off now — look after them, P{pos}.",
        "The rubber's worn, mate. Smooth inputs, make them last.",
        "Tyre wear is high — manage them home, don't overdrive.",
        "Those tyres are tired now. Ease the loads, bring it home.",
        "Grip's dropping with the wear, P{pos}. Be gentle through the quick stuff.",
    ],
    # periodic lap-count update so you always know where you are in the race.
    # {togo} laps remaining, {done} completed, {total} race length
    "laps_update": [
        "{togo} laps to go, P{pos}. Keep it steady.",
        "We're {done} of {total} laps in — {togo} to run. Looking good.",
        "{togo} laps left, P{pos}. Settle into the rhythm.",
        "Just over halfway feeling — {togo} laps remaining. Keep pushing.",
        "{togo} to go, mate. Manage it and bring it home.",
        "Lap {done} of {total} done. {togo} left, you're doing great.",
    ],
    # countdown calls in the closing laps (fire once each at 5 / 3 / 2 to go)
    "laps_countdown": [
        "{togo} laps to go now, P{pos} — you've got this.",
        "Right, {togo} laps left. Heads down, finish the job.",
        "{togo} to go, mate. Big finish now, stay focused.",
        "Into the final {togo} laps, P{pos}. Everything you've got.",
        "{togo} laps remaining — this is where it counts.",
    ],
    # TIMED-race closing countdown — fired once each at 10/5/2/1 minutes to go.
    # {mins} is a ready-made phrase ("5 minutes" / "1 minute").
    "mins_countdown": [
        "{mins} to go on the clock, P{pos}. Big finish now, stay focused.",
        "We're into the final {mins}, P{pos} — everything you've got.",
        "{mins} left on the timer, mate. This is where it counts.",
        "Clock's down to {mins}, P{pos}. Heads down, bring it home.",
        "Just {mins} remaining now — no mistakes, finish the job.",
        "{mins} to run, P{pos}. Manage it and get this one home.",
        "Final {mins} on the clock — give me everything you've got left.",
    ],
    # timed-race version (no lap count). {mins} minutes left
    "time_update": [
        "About {mins} minutes left, P{pos}. Keep it tidy.",
        "{mins} minutes to go, mate. Manage the race.",
        "Roughly {mins} minutes remaining, P{pos}. Stay sharp.",
        "Clock's at {mins} minutes, keep doing what you're doing.",
    ],
    # all-good reassurance — gap healthy, no damage, keep pushing
    "status_good": [
        "Gap's good, no damage, the car's healthy. Keep pushing, P{pos}.",
        "All looking good here — pace is strong, car's fine. Keep it up.",
        "Everything's healthy our end, P{pos}. Lovely pace, stay on it.",
        "No issues at all, mate. Gap's under control. Keep pushing.",
        "Car's in good shape, times are mega. Exactly what we want, P{pos}.",
        "Everything green on our end, P{pos}. Lovely pace, no worries — push on.",
        "No issues anywhere, mate. Tyres good, gap good. Keep delivering, P{pos}.",
        "Car feels strong, times consistent. We're in great shape, P{pos}.",
        "All healthy here, P{pos}. You've got the pace — just keep it clean.",
        "Temps are good, wear is fine, you're flying. Carry on, P{pos}.",
        "Nothing to report but good news, P{pos}. Stay on it, this is mega.",
    ],
    # you need to make your (mandatory) pit stop — the window is open
    "pit_needed": [
        "Pit window's open, P{pos} — you need to make your stop.",
        "Time to box, mate — get your mandatory stop done.",
        "The pit window is open. Don't leave your stop too late.",
        "We need that pit stop, P{pos}. Box when you're ready.",
        "Mandatory stop still to come — pit window's open now.",
    ],
    # a penalty is sitting unserved — remind the driver to serve it
    "penalty_serve": [
        "Reminder: you've still got that penalty to serve. Don't leave it.",
        "Don't forget the penalty, mate — serve it before the flag.",
        "That penalty's still outstanding. Get it served, P{pos}.",
        "Serve the penalty when you can — we can't risk it to the end.",
    ],
    # damage bad enough that it needs a repair in the pits. {part} = which
    "pit_damage": [
        "That {part} damage is serious — we need to box and repair it.",
        "The {part}'s badly hurt, P{pos}. Box this lap, we'll fix it.",
        "We have to pit for that {part} damage — it's costing too much.",
        "Get it to the pits, mate — the {part} needs replacing.",
    ],
    # tyres critically worn — pit for fresh rubber. ONLY used when a stop is
    # actually on the cards (mandatory window or strategy); otherwise we warn
    # without nagging to box (see "tyres_gone").
    "pit_tyres": [
        "Tyres are done, P{pos} — we need to box for fresh rubber.",
        "Those tyres are finished. Box this lap for a fresh set.",
        "We can't go on like this — pit for new tyres, mate.",
        "Tyre wear is critical now. Get in for fresh ones, P{pos}.",
    ],
    # tyres critically worn but there's NO stop planned — manage them to the
    # flag rather than telling the driver to pit (which would be wrong advice
    # in a no-stop race). Honest about the loss of grip, but never naggy.
    "tyres_gone": [
        "Tyres are properly gone now, P{pos} — no stop, so we nurse these home. Smooth as you can.",
        "Rubber's shot, mate, but we're not boxing. Manage the grip, short-shift, baby the throttle.",
        "These tyres are finished but we run to the end on them. Brake earlier, ease the loads, bring it home.",
        "Grip's falling off a cliff, P{pos}. No fresh set coming — drive around it, protect the rears.",
        "Tyres are cooked. We commit to the finish on these, so be gentle and think about traction zones.",
        "No more grip left in them, mate. We hold station and survive — slow in, smooth out, mind the kerbs.",
        "They're done, but so is everyone else's rubber. Manage it better than them and we keep the place.",
    ],
    # overtake acknowledgement WITH a track location ({where} = "into Turn 6" /
    # "into Eau Rouge" / "in the final sector"). Used when the engine could place
    # the pass; otherwise the plain "gained" pool is used.
    "gained_where": [
        "Lovely move {where} — up to P{pos}!",
        "That's the pass done {where}. P{pos} now, keep hunting.",
        "Got him {where}! P{pos}, eyes up for the next one.",
        "Brilliant move {where} — P{pos}. On you go.",
        "P{pos}! Made that one stick {where}. Tidy work.",
        "That's how it's done {where} — P{pos}, keep the momentum.",
        "Cleanly done {where}. P{pos}, next car's already in range.",
        "Up to P{pos} with a great move {where}. Eyes forward.",
    ],
    # PROACTIVE per-section coaching — fired as you enter a new sector. {sec} =
    # sector number (1/2/3); {tip} = a real track tip for the lap ahead.
    "section_ahead": [
        "Sector {sec} coming up — {tip}",
        "Into sector {sec} now. {tip}",
        "Heads up for sector {sec}: {tip}",
        "This next sector, P{pos} — {tip}",
        "Coming into sector {sec} — {tip}",
        "Through sector {sec} here. {tip}",
    ],
    # car damage picked up. {part} = engine / suspension / etc.
    "damage": [
        "We've taken some {part} damage — nurse it, but keep going.",
        "There's {part} damage there, mate. Adjust your style, look after it.",
        "Picked up {part} damage. It'll cost some pace — manage it.",
        "That contact's hurt the {part}. Keep it together, we can still finish.",
        "Some {part} damage showing on our end. Be mindful, bring it home.",
    ],
    # TYRE TEMPERATURE — read off the centre-tread temps vs the car's own
    # optimal/cold/hot references. {ax} = "fronts" / "rears" / "tyres".
    "tyre_cold": [
        "Those {ax} are still cold, mate — work some temperature in before you lean on it.",
        "The {ax} aren't up to temperature yet. Give them a lap, build it in gradually.",
        "Careful — {ax} are below working temp. Wind the loads up slowly, no big inputs.",
        "Not much heat in the {ax} yet. Be patient, bring them in before you really push.",
        "{ax} are cold still. Weave a little, get some temperature in before the quick stuff.",
    ],
    "tyre_hot": [
        "You're starting to cook the {ax} — ease the entry and let them breathe.",
        "The {ax} are over temperature, mate. Back the loads off a fraction to bring them down.",
        "Watch the {ax} — they're overheating. Smooth inputs, give them a chance to recover.",
        "Temps climbing on the {ax}. Short-shift where you can and stop sliding it.",
        "The {ax} are getting too hot — you're scrubbing grip. Manage them for a lap or two.",
    ],
    # overheating specifically from sitting in another car's dirty air
    "tyre_hot_traffic": [
        "The {ax} are overheating in this dirty air — drop back half a second to cool them.",
        "Sitting this close is cooking the {ax}, mate. Give yourself a gap, let them breathe.",
        "You're losing the {ax} in the turbulence. Back off a touch, then have another go.",
        "Those {ax} are over temp in the wake of that car — ease off, cool them, attack fresh.",
    ],
    # BRAKE TEMPERATURE — brake over its hot reference -> fade risk.
    # {ax} = "front" / "rear" / "front and rear".
    "brake_hot": [
        "The {ax} brakes are getting hot — short-shift and give them air down the straights.",
        "Watch the {ax} brakes, mate, temps are high. Brake a fraction earlier, let them cool.",
        "{ax} brakes are over temperature — ease the pedal pressure or we'll get fade.",
        "Heat building in the {ax} brakes. Lift and coast a little to bring them back.",
    ],
    # ENGINE TEMPERATURE (mechanical sympathy) — a large, sustained rise above
    # this car's own warmed-up running temp. No {kw} needed.
    "engine_hot": [
        "Water temp's creeping up, mate — ease off a touch and let the engine breathe.",
        "Engine's running hot. Short-shift and lift a little, bring those temps back down.",
        "Temperatures climbing on the engine — back the pace off a lap, we need to cool it.",
        "We're getting warm under the bonnet. Lift and coast where you can, protect the engine.",
    ],
    # engine overheating WITH damage present — the cooling is compromised
    "engine_hot_dmg": [
        "That damage is choking the cooling — water temp's climbing. Ease right off or we'll cook it.",
        "Engine temps are spiking with that damage, mate. Manage the pace, we cannot lose this engine.",
        "The cooling's compromised after that knock — back off and keep the temperatures in check.",
    ],
}

# SECTOR-TIME COACHING — the engineer reads your last lap's sector splits against
# your own best (and the session best) and tells you exactly where the time is.
# Used in EVERY session. {sec}/{one}/{two} = sector numbers, {d} = time lost,
# {gd} = time you're up. Genuinely useful, specific feedback — never generic.
SECTOR_COACH = {
    # one sector is clearly costing you the most vs your own best
    "slow": [
        "You're leaving about {d} in sector {sec} — that's where the lap's hiding.",
        "Sector {sec}'s the weak one, roughly {d} off your best there. Have a look at your lines.",
        "We're losing {d} in sector {sec}, mate. Get that one right and the lap drops.",
        "Sector {sec} is costing you, about {d} down. The pace is there everywhere else.",
        "Bit untidy in sector {sec} — {d} adrift of your best. Focus your next lap there.",
        "Most of your time loss is sector {sec}, {d} of it. Smooth that section out.",
        "You're a touch slow in sector {sec}, around {d}, but keep the pace up — the rest is mega.",
        "Sector {sec}'s the one to find — {d} in it. Commit a bit more there and it's a big step.",
        "Talk me through sector {sec} — you're {d} off your best in there. Something's not hooking up.",
        "If we clean up sector {sec} you're a different driver — {d} sat in that one section.",
        "Watch sector {sec}, {d} lost. Maybe a braking marker too early or a lazy exit.",
        "Pace is strong but sector {sec} is leaking {d}. Same commitment as the rest and it's gone.",
    ],
    # one sector strong AND one weak — the classic "great here, costing there"
    "mixed": [
        "Sector {one} was mighty, but you gave it back in sector {two} — {d} of it. Marry the two up.",
        "Brilliant through sector {one}, then {d} dropped in sector {two}. Carry that pace across.",
        "Sector {one}'s right on the limit, sector {two}'s {d} off. Find the same in the slow one.",
        "Lovely sector {one}, mate. Sector {two}'s the homework — {d} to claw back there.",
        "You're flying in sector {one} but tentative in sector {two}, {d} of it. Trust the car there too.",
        "Mixed bag — sector {one} purple-quick, sector {two} {d} down. Tidy the weak one and it's a lap.",
        "Sector {one} is exactly it. Now do that in sector {two}, where you're {d} adrift.",
    ],
    # a single sector was genuinely the best you've done / matched the field
    "strong": [
        "Sector {sec} was your best yet — whatever you changed, keep doing it.",
        "That's a cracking sector {sec}, mate. Right on the money. Bank that line.",
        "Sector {sec} was mega that lap — fastest you've managed there. More of the same.",
        "Purple-quick in sector {sec}! That's the benchmark now, repeat it.",
        "Sector {sec} was outstanding — quickest of anyone through there. Brilliant.",
        "Big improvement in sector {sec}, that's the way. Now string it with the rest.",
    ],
    # a clean, consistent lap — close to best across all three
    "solid": [
        "Lovely lap — all three sectors right on your best. Nothing to change, just repeat it.",
        "Beautifully balanced, mate. Every sector's there. That's the lap, do it again.",
        "Spot on across the board. No weak sector that lap — exactly what we want.",
        "Consistent everywhere, all three splits on it. That's a proper lap, bank it.",
        "Tidy in every sector. Nothing wasted — keep delivering that and we're golden.",
        "Three green sectors, mate. That's the rhythm. Lock it in.",
    ],
}

# NATIVE-LANGUAGE driver radio: tier-C rivals key the mic in their own tongue.
# Each entry is (spoken_native, english_subtitle) — the audio is the native text,
# the on-screen bubble shows the English. Generic racing chatter (no names/gaps),
# so it always fits. Keyed by language code (see tts.NATIVE_VOICE_LANG).
NATIVE_RADIO = {
    "fr": [
        ("Allez, allez! Je le tiens!", "Come on, come on! I've got him!"),
        ("Il est juste derrière moi!", "He's right behind me!"),
        ("Quelle course, incroyable!", "What a race, incredible!"),
        ("Je n'abandonne pas, jamais!", "I'm not giving up, never!"),
        ("Laissez-moi passer, j'ai le rythme!", "Let me through, I've got the pace!"),
        ("Pas de souci, je gère.", "No worries, I've got it under control."),
        ("C'était limite, mais ça passe!", "That was close, but it works!"),
        ("Mes pneus sont finis!", "My tyres are finished!"),
        ("On y est presque, tiens bon!", "We're almost there, hold on!"),
        ("Je remonte, je remonte!", "I'm climbing back, climbing back!"),
    ],
    "pt": [
        ("Vamos, vamos! Tô voando!", "Come on, come on! I'm flying!"),
        ("Ele tá colado em mim!", "He's stuck right on me!"),
        ("Que corrida, que demais!", "What a race, awesome!"),
        ("Não vou desistir nunca!", "I'm never giving up!"),
        ("Deixa eu passar, tenho ritmo!", "Let me through, I've got the pace!"),
        ("Tá tranquilo, tô no controle.", "It's calm, I'm in control."),
        ("Foi por pouco, mas consegui!", "That was close, but I made it!"),
        ("Meus pneus já era!", "My tyres are gone!"),
        ("Tamo quase lá, segura!", "We're almost there, hold on!"),
        ("Tô recuperando posições!", "I'm clawing back positions!"),
    ],
    "ru": [
        ("Давай, давай! Я его держу!", "Come on, come on! I've got him!"),
        ("Он прямо за мной!", "He's right behind me!"),
        ("Какая гонка, невероятно!", "What a race, incredible!"),
        ("Я не сдаюсь, никогда!", "I'm not giving up, never!"),
        ("Пропусти меня, у меня темп!", "Let me through, I've got the pace!"),
        ("Всё нормально, я контролирую.", "Everything's fine, I'm in control."),
        ("Было близко, но прошло!", "That was close, but it worked!"),
        ("Мои шины убиты!", "My tyres are dead!"),
        ("Почти приехали, держись!", "Almost there, hold on!"),
        ("Я отыгрываю позиции!", "I'm clawing back positions!"),
    ],
}

# SESSION-NEUTRAL native chatter for PRACTICE / QUALIFYING — about laps and pace,
# never race battles, so a foreign-voice rival doesn't sound like they're racing
# when they're just putting a lap in. Same (native, English-subtitle) format.
NATIVE_RADIO_QUALI = {
    "fr": [
        ("Bon tour, ça vient!", "Good lap, it's coming together!"),
        ("La voiture est bien équilibrée.", "The car feels well balanced."),
        ("Je pousse, encore un peu de temps à trouver.", "Pushing hard, a bit more time to find."),
        ("Presque le tour parfait!", "Almost the perfect lap!"),
        ("Il me faut un tour propre.", "I just need a clean lap."),
        ("Les pneus sont dans la fenêtre.", "The tyres are in the window now."),
    ],
    "pt": [
        ("Boa volta, tá vindo!", "Good lap, it's coming together!"),
        ("O carro tá bem equilibrado.", "The car feels well balanced."),
        ("Tô forçando, falta pouco tempo.", "Pushing hard, a little more time to find."),
        ("Quase a volta perfeita!", "Almost the perfect lap!"),
        ("Preciso de uma volta limpa.", "I just need a clean lap."),
        ("Os pneus tão na temperatura.", "The tyres are up to temperature now."),
    ],
    "ru": [
        ("Хороший круг, прогресс есть!", "Good lap, making progress!"),
        ("Машина хорошо сбалансирована.", "The car feels well balanced."),
        ("Давлю, ещё немного времени найти.", "Pushing hard, a bit more time to find."),
        ("Почти идеальный круг!", "Almost the perfect lap!"),
        ("Нужен чистый круг.", "I just need a clean lap."),
        ("Шины вышли на температуру.", "The tyres are up to temperature now."),
    ],
}

# When a driver you recently overtook fights back and re-passes you.
REVENGE = [
    "Get back here, {who}! That's my place!",
    "You're NOT keeping that, {who}!",
    "Payback. Told you I'd be back, {who}.",
    "Did you forget about me, {who}? I'm right here.",
    "That's how it's done. Stay behind, {who}.",
    "Nice try, {who}. Now it's MY turn again!",
    "You didn't think I'd let that go, did you, {who}?",
    "Right back at you, {who}! That position's mine.",
    "Enjoy it while it lasted, {who} — I want it back!",
    "Not so fast, {who}! I've got an answer for that.",
    "Tit for tat, {who}. We're not done here.",
    "You poked the bear, {who}. Have your place back!",
    "Welcome to the fight, {who} — and goodbye!",
    "That's the repass! Sit down, {who}.",
    "I warned you, {who}. Straight back through!",
]

# A driver takes the lead (P1).
LEAD = [
    "I've got the lead! P1, let's build a gap.",
    "We're out front now! Keep it clean.",
    "Into the lead! This is ours to lose.",
    "P1! Head down, hammer it home.",
    "That's the lead! Now I control this race.",
    "Top spot is mine — time to stretch my legs!",
    "P1 and pulling away. This feels good!",
    "Lead is ours! Stay focused, manage the gap.",
    "I'm in front! Let's make this one count.",
    "Out front and loving it — keep it clean, keep it quick.",
    "We've hit the front! Now build a cushion.",
    "P1! Eyes forward, no mistakes from here.",
    "Got the lead at last! Dictate the pace now.",
    "Front of the field — exactly where we want to be!",
]

# Drivers reacting on the radio to their FINISHING position as they cross the
# line. Keyed by outcome tier; the winner's celebration is always aired first.
DRIVER_FINISH = {
    "win": [
        "YES! That's the win! WE WON IT! Get in there!!",
        "P1 baby! Champagne's on me! What a race!",
        "Victory is OURS! I love this team! Whoooo!",
        "We've done it! First place! Absolutely buzzing!",
        "Chequered flag and we're P1! Mega, mega job everyone!",
        "That's how you win a race! Unbelievable! P1!",
        "WE ARE THE WINNERS! Oh, that feels good! P1!",
        "Get in there!! P1! I could kiss every one of you!",
        "Flag's out and we're FIRST! Dreamland, this!",
        "P1! P1! Tell me that just happened! Incredible!",
    ],
    "podium": [
        "P{pos}! On the podium! I'll take that all day!",
        "Get in! P{pos}, that's a trophy! Brilliant work!",
        "Podium, baby! P{pos}! What a result for us!",
        "P{pos} and a spot on the rostrum. Love it!",
        "We're on the box! P{pos}! Cracking race!",
        "Trophy time! P{pos}! That's a brilliant day's work!",
        "P{pos}! Spraying champagne tonight, boys!",
        "On the podium, P{pos}! Knew we had it in us!",
    ],
    "points": [
        "P{pos} at the flag. Solid points, I'll take it.",
        "Good points in the bag, P{pos}. Decent day.",
        "P{pos}. Not the podium, but we scored. Onwards.",
        "Brought it home P{pos}. Steady, points on the board.",
        "P{pos}. We'll build on that one, good effort.",
        "P{pos}. Banked it, no dramas. That'll do nicely.",
        "Job done, P{pos}. Points are points, mate.",
        "P{pos} and home safe. Tidy, professional stuff.",
    ],
    "low": [
        "P{pos}. Tough race, that one. We move on.",
        "Just nothing there today, P{pos}. Frustrating.",
        "P{pos} at the flag. Not our day, we regroup.",
        "Long afternoon. P{pos}. We'll come back stronger.",
        "P{pos}. Glad that one's over, honestly.",
        "P{pos}. Chalk it up and forget it, mate.",
        "Nothing went our way, P{pos}. Next time.",
        "P{pos}. Bruising one, that. Heads up, we learn.",
    ],
}

# Engineer feedback in PRACTICE / QUALIFY — pace & run notes, not race talk.
ENGINEER_PRACTICE = {
    # ENGINEER session opener — greeting + {trk}; the code appends a piece of
    # track knowledge then a warm-up tail ("intro_tail").
    "intro_practice": [
        "Right, we're in practice here at {trk} today.",
        "OK, practice session at {trk} — let's get to work.",
        "Morning. Practice at {trk}, time to dial this car in.",
        "Here we go — practice at {trk}. Plenty to learn today.",
        "Practice session at {trk}, mate. Let's build up nicely.",
        "Alright, we're out for practice at {trk}.",
    ],
    "intro_quali": [
        "Right, this is qualifying at {trk} today.",
        "OK, qualifying at {trk} — let's go find a lap.",
        "Here we go, mate — qualifying at {trk}.",
        "Qualifying at {trk} now. This one's all about the perfect lap.",
        "Alright, quali at {trk}. Let's put it on the grid.",
        "Time to qualify at {trk}. Heads down.",
    ],
    "intro_tail": [
        "Get some clean laps in and warm the tyres up before you start pushing.",
        "Bank a few laps first, get heat in the tyres and brakes, then we attack.",
        "Build up gradually — temperature in the tyres before the big lap.",
        "No rush early on; warm everything up, then lean on it.",
        "Settle in, get the tyres in the window, then show me what we've got.",
        "Take a couple of laps to feel it out, then start turning up the wick.",
    ],
    "practice": [
        "Good lap. Keep building, learn the limit.",
        "Looking comfortable out there. Bank a few more.",
        "Pace is coming. Work on your braking points.",
        "Nice and consistent. Let's find a bit more in sector two.",
        "Tyres are coming in. Push when you're ready.",
        "That's a tidy run. Keep stringing them together.",
        "Looking after the car nicely. We'll dial the setup in.",
        "Decent balance now. How's the rear feeling to you?",
        "Good baseline lap. Let's try a little more front wing.",
        "No need to force it — just bank the mileage for now.",
        "Brakes are up to temp. Lean on them a bit more.",
        "Happy with that long run. The tyre deg looks healthy.",
        "Take a breather, then we'll go again with fresh boots.",
        "How's the front end on turn-in? We can trim the balance if you want.",
        "Let's do a few more on this set — I want to see how the deg looks.",
        "Try a higher gear through the medium-speed stuff, see if it settles the rear.",
        "Reference your braking markers — be consistent and the speed will come.",
        "We've got fuel for a long run — use it, build the rhythm.",
        "That's the balance window we wanted. Now just rack up clean laps.",
        "Don't chase the perfect lap yet — learn the track, the time follows.",
        "Good data on that run. We'll firm up the rear before the next set.",
        "Work the kerbs gently for now — we'll commit to them once you're comfortable.",
        "Smooth is fast here. Settle in, no need to overdrive it.",
        "Tell me where you want more grip and we'll chase it with the setup.",
        "Nice progression. Every lap you're learning where the limit really is.",
        "Brakes and tyres are in the window now — this is when the real pace comes.",
    ],
    "qualify": [
        "Track's clearing — find some space for a hot lap.",
        "Quali run now. Get the tyres in the window.",
        "Big lap when you're ready. Everything's got to be perfect.",
        "Clean air ahead. Send it on this one.",
        "Find a gap and let it rip — we need the time.",
        "This is the one. Commit, every tenth counts.",
        "Push lap now — build the tyres on the out-lap first.",
        "Gap behind is good. Clear track, go and grab it.",
        "Last run coming up. Leave nothing out there.",
        "Tyres are prime. This is your moment — nail it.",
        "One warm-up lap to get temperature in, then send the next one.",
        "Build the brakes on the out-lap — they need heat to bite for the flyer.",
        "You've got clear road for two laps — use the first to prep, second to deliver.",
        "Track's rubbered in and grip is peaking — this is the lap to grab.",
        "Don't leave anything in the bank — every corner, full commitment.",
        "Mind the tyres on the out-lap, then it's everything you've got.",
        "Watch for traffic in the final sector — back off and reset if it's there.",
        "This is where it counts — one clean lap, no mistakes, go get pole.",
    ],
}

# Engineer QUALIFYING feedback — DATA-DRIVEN and genuinely useful: provisional
# position, gap to pole, personal bests, when to push. {pos}=provisional place,
# {gap}=gap to pole, {best}=your best lap.
ENGINEER_QUALI = {
    "pole": [
        "That's provisional POLE, mate! Superb lap, P1!",
        "Top of the timesheets — you're on provisional pole! Mega!",
        "Get in! Quickest of all. P1, that's pole as it stands!",
        "P1! Fastest of anyone out there. Brilliant lap.",
        "Provisional pole! Nobody's touched that. Outstanding driving.",
        "You're top of the sheets — that's pole position as it stands. Mighty lap.",
        "P1! The car's hooked up and so are you. Pole, provisionally.",
        "That's the benchmark now — provisional pole. The rest are chasing you.",
        "Quickest of the lot! Pole as it stands, mate. Lovely, lovely lap.",
    ],
    "improve": [
        "Better lap — provisional P{pos} now, {gap} off pole.",
        "That's quicker, P{pos}. {gap} to the top, keep chipping away.",
        "Up to P{pos}, mate. {gap} off pole — there's more in it.",
        "Improvement! P{pos} provisionally, {gap} to pole.",
        "Good, that's P{pos} now. {gap} away from top spot.",
        "Step in the right direction — P{pos}, {gap} to pole. Keep stacking it up.",
        "Quicker again, P{pos}. The gap to pole's down to {gap}. We're coming.",
        "That's progress — P{pos}, only {gap} off the top now. One more push.",
        "Building nicely, P{pos}. {gap} to pole and there's still time in the car.",
    ],
    "hold": [
        "Provisional P{pos}, {gap} to pole. We need a bit more.",
        "Sitting P{pos} for now — {gap} off the top. Let's find it.",
        "P{pos} on the grid as it stands, {gap} to pole.",
        "You're P{pos}, {gap} adrift of pole. Time to dig deep.",
        "Currently P{pos}. {gap} to find — the pace is in the car.",
        "We're P{pos}, {gap} shy of pole. One clean lap turns that around.",
        "Holding P{pos}, mate. {gap} to the top — it's there if we tidy up.",
        "P{pos} as it stands. {gap} the deficit. Don't force it, just link it together.",
    ],
    "push": [
        "Track's at its best now — go and get a lap in.",
        "Clear air ahead, this is your window. Send it.",
        "Tyres are in, this is the one. Everything you've got.",
        "Grip's coming up as the track rubbers in — push now.",
        "This is your lap. Commit to every corner.",
        "Conditions are peaking — now's the time, leave nothing out there.",
        "Best of the track right now, mate. Wind it up and let it rip.",
        "Window's open, tyres are prime. This is the lap to grab it.",
        "Go and take it — clear road, good grip, no excuses. Send it.",
    ],
    "pb": [
        "That's your best of the session — lovely stuff.",
        "New personal best, mate. The pace is right there.",
        "Quickest you've gone all session — keep building.",
        "Best lap yet. That's the benchmark, now beat it.",
        "Personal best! The improvement's coming lap on lap. Keep it going.",
        "That's your quickest, mate — chipping away nicely. More to come.",
        "New best for you. Confidence is building, you can see it in the times.",
        "Best lap of the day so far — you're finding the limit nicely.",
        "Quicker again! Every lap a little sharper. Lovely progression.",
        "That's a personal best, mate. The car's coming to you now.",
        "New benchmark for you there — keep stacking the tenths.",
        "Fastest you've gone — the rhythm's there, now go and beat it.",
    ],
    "traffic": [
        "You caught traffic there — abort and reset for another go.",
        "Bin that lap, you had a car right in the way. Go again.",
        "Traffic ruined that one. Cool the tyres, we'll retry.",
        "Yellow sector cost you — back off, we'll get another lap.",
        "Car parked in your braking zone there — scrub that, build a gap, go again.",
        "That's a write-off with the traffic. Drop back, get clear air, reset.",
    ],
    # YOUR flying lap was DELETED for exceeding track limits
    "deleted": [
        "That lap's been deleted — you ran wide. Keep it within the lines next time.",
        "Lap deleted, mate, track limits. Reset and go again, mind the white lines.",
        "We've lost that one — exceeded limits. Tidy it up and have another go.",
        "Deleted, I'm afraid — all four wheels over. Rein it in a touch.",
        "That time won't count, you went beyond the limits. Next lap, keep it clean.",
        "Gone — track limits took it. So close to the edge, just pull it back a foot.",
        "Lap's chalked off, mate. You're carrying so much speed you're running out of road. Ease the exit.",
        "Deleted again — the limits are biting us. Pick a tighter line on the exits.",
    ],
    # you completed a lap but it was OFF your best
    "offbest": [
        "That's off your best, P{pos}. Have another go, the time's in there.",
        "Not quite, a bit slower that lap. Reset and build to it.",
        "Down on your best by a fraction. Cool the tyres, go again.",
        "Slower lap that one — {gap} off pole still. Tidy the corners up.",
        "We left a bit out there. Have another crack at it.",
        "A touch down on that one, P{pos}. The time's still in the car — go again.",
        "Slightly slower, mate, but no dramas. Reset, cool them, deliver the next one.",
        "Not your best that lap — shake it off, the pace is still there.",
        "Bit scrappy, P{pos}. Cool the tyres, regroup, have another crack.",
        "Off the pace that time. No panic — one clean lap and it's back.",
        "We left a little out there, P{pos}. Tidy the corners, go again.",
        "Couple of tenths down, mate. Reset the rhythm and deliver next time.",
    ],
    # track limits again — this lap AND the next are void (lap_valid_state == 2)
    "nextlap": [
        "That's this lap and your NEXT lap gone for track limits — pull it back inside.",
        "Careful, mate — you've just lost this lap and the next one. Tidy the exits up.",
        "Both this lap and the next won't count now. Give the white lines some room.",
        "Track limits again — current and next lap both invalid. Rein it in a touch.",
        "Heads up, that's two laps void — keep all four wheels in from here.",
    ],
    # you ran off the TRACK LIMITS (cut_track_warnings ticked) — milder than a
    # spin, but warn every single time so you keep it clean.
    "limits": [
        "Watch the limits there, mate — all four wheels stayed inside, please.",
        "That's a track-limits warning — keep it within the white lines.",
        "Ran a touch wide that time. Tighten the line up, mind the limits.",
        "Careful with the track limits — we can't have laps deleted in qualifying.",
        "You're flirting with the white lines — rein the exits in a fraction.",
        "Bit greedy on the kerb there. Keep all four on the road for me.",
        "Track limits, mate — pull it back a foot and we're golden.",
        "Mind the edges — that's a warning, let's not make a habit of it.",
    ],
    # you went genuinely OFF (spin / grass / gravel) in practice or qualifying
    "offtrack": [
        "Whoa — keep it on the island, mate! You all right? Gather it up and reset.",
        "That's a big moment — off the track there. Take a breath, build a fresh lap.",
        "Careful! You lost it that time. Cool the tyres, no rush, we'll go again.",
        "Off the road, mate — that'll have flat-spotted the tyres. Steady lap to scrub them, then push.",
        "Easy — that's how you bin it in quali. Reset, clear your head, the pace is still there.",
        "Ran out of road there. No harm done in practice — learn the limit and dial it back a notch.",
        "That excursion cost you the lap. Get it back on, settle the tyres, build up again.",
        "Too greedy that time and it bit you. Bring it back, calm lap, then have another go.",
    ],
}

# Rival QUALI/PRACTICE radio — drivers react to the SESSION (no race overtakes):
# a flier, provisional pole, traffic, a scrappy lap. Kept rare (flavour only).
RIVAL_QUALI = {
    "pole": [
        "Pole! That's what I'm talking about! The car feels mega!",
        "Quickest of all! Get in there, what a lap!",
        "Top of the times! Beautiful, the car's hooked up!",
        "Provisional pole, baby! That's the one!",
    ],
    "good": [
        "Good lap, that. Happy with it — plenty more to come.",
        "That'll do nicely. Tyres felt great through there.",
        "Solid lap. We're in the window now.",
        "Yeah, decent. There's still a bit more in it.",
        "Car's hooked up nicely — I can lean on it now.",
        "That felt clean. Confidence is building lap on lap.",
        "Balance is spot on through there. Happy with the run.",
        "Found a bit in the middle sector — there's more where that came from.",
    ],
    "traffic": [
        "Traffic! Are you kidding me, that cost me the lap!",
        "I had a car right in my way — lap absolutely ruined!",
        "Yellows and traffic, useless lap that. Going again.",
        "Whoever that was just cost me three tenths!",
        "Backmarker in the worst place — there goes the lap.",
        "Stuck behind someone on a slow lap, completely killed my rhythm!",
        "Why is he sitting on the racing line?! Lap's gone.",
    ],
    "scrappy": [
        "Lost the rear in sector two — scrap that lap.",
        "Messy, that one. I'll have to go again.",
        "Not good enough, I left time out there.",
        "Locked up into the hairpin, that lap's gone.",
        "Ran wide on the exit, time's gone — resetting.",
        "Too greedy on the kerbs, unsettled it. Bin that one.",
        "Snap of oversteer cost me — I'll tidy it up next time.",
        "Missed the apex and paid for it. Going again.",
    ],
    # reacting to SOMEONE ELSE going fastest — time to respond
    "chasing": [
        "Someone's gone quicker — right, my turn.",
        "That's the time to beat now. Let's go and get it.",
        "Quick lap from someone up there. I've got more in me.",
        "Right, the gauntlet's down. Time to respond.",
        "Okay, that's the benchmark. Let's go beat it.",
    ],
}

# Famous real motorsport radio lines, dropped in OCCASIONALLY as flavour (a
# small chance per rival message) — easter eggs for fans, never every line.
EASTER_EGGS = {
    "overtaken": [
        "Oh, this guy thinks he's Max Verstappen!",
        "He can't do that — he's just DONE it!",
        "Whoa! Is that them?! Is that them past me?!",
        "He came from nowhere! Where did he come from?!",
        "Is that Glock?! He's catching them on the line!",
        "He overtook me on the outside, that's just not normal!",
        "Where did he come from?! He was nowhere a lap ago!",
    ],
    "caught": [
        "Leave me alone, I know what I'm doing!",
        "It's hammer time — he's all over me!",
        "My tyres are gone! They're completely gone back here!",
        "Tell him to stay behind, this is a team thing!",
        "I am stuck behind, I can't... look, just leave me to it!",
        "I'm giving it everything I've got, everything!",
        "Bono, my tyres are gone, the tyres are gone!",
        "Just leave me to it, I'll hold this position!",
    ],
    "crash": [
        "It was just a racing incident, that's all it was!",
        "GP2 engine! GP2! Arghhh!",
        "No, no, NO! ...okay. Okay. I'm okay.",
        "That is not fair! That is just NOT fair!",
        "He just turned in on me! He turned in on me!",
        "I can't believe it! After everything, it ends like this!",
        "What happened?! What... what just happened to me?!",
    ],
    "taunt": [
        "Get in there! Yes! Simply lovely!",
        "Smooth operator — that's how it's done!",
        "To be the man, you've gotta beat the man!",
        "Multi twenty-one? Not today. I'm not moving over.",
        "I am the best driver out here, and I just proved it!",
        "Still I rise! Did you see that one?!",
        "That, my friends, is how it is done!",
    ],
}

# Mood interjections, prepended when a driver is on a losing/winning streak.
MOOD_FRUSTRATED = ["Unbelievable.", "For god's sake.", "Come ON.",
                   "This is a nightmare.", "Every single lap..."]
MOOD_PUMPED = ["Yes!", "Let's GO!", "Get in!", "On fire today!", "Feeling good!"]

# ---- play-by-play commentary (third-person, whole-field, broadcast booth) ----
# {drv}=subject  {oth}=other driver  {pos}=position  {gap}=gap/time  {trk}=track
COMMENTARY_LINES = {
    "start": [
        # 5 fresh "lights go out" variations so the start sounds different each race
        "And the lights go out! {drv} leads them away at {trk}!",
        "Lights out, and away we go! It's {drv} with the lead into turn one!",
        "The lights go out — and we are RACING at {trk}, {drv} out in front!",
        "Five red lights... and they're gone! {drv} heads the charge at {trk}!",
        "And the lights go out at {trk}! {drv} streaks into the lead!",
        "Lights out and away we go here at {trk} — {drv} defending the lead into turn one!",
        "Lights out and away we go! {drv} leads the field into the first corner at {trk}!",
        "And they're away at {trk}! {drv} defending the lead into turn one!",
        "Lap one is underway here at {trk}, and {drv} leads them away!",
        "And we are racing at {trk}! {drv} tries to convert the lead off the line!",
        "Green flag, green flag! {drv} heads the pack into the opening lap!",
        "It's lights out and away we go — {drv} out in front at {trk}!",
        "We're racing at {trk}! {drv} leads as they stream down to turn one!",
        "Lap one of the race, and {drv} is trying to keep the lead at the head "
        "of the pack!",
        "The flag drops at {trk} and they pour into turn one — {drv} leading!",
        "A clean getaway for the field, {drv} holding sway at the front!",
        "Here they come on lap one — {drv} fending them off into the first corner!",
        "The race is on at {trk}! {drv} streaks away at the head of affairs!",
        "Wheels spinning, elbows out — {drv} leads them through the opening exchanges!",
        "And they're away! {drv} makes the cleaner start to lead the charge!",
        "Lap one chaos brewing behind, but {drv} is clear at the front!",
        "The lights go green and {drv} grabs the early initiative at {trk}!",
        "Off they go! {drv} converts pole into the lead through turn one!",
        "Lights out and away we go! {drv} defending that lead hard into turn one!",
        "And we're racing at {trk}! It's {drv} leading, fending off the pack into the first corner!",
        "The lights go out and away we go — {drv} keeps the hammer down to hold the lead!",
        "Five lights and away! {drv} gets the jump and leads them through turn one!",
        "Lights out! Down to turn one they go, {drv} holding firm at the front!",
        "And away we go at {trk}! {drv} squeezes the lead through the opening corner!",
        "It's lights out and away we go — {drv} covering the inside into turn one!",
        "The lights blink out and the pack surges — {drv} clings to the lead at {trk}!",
        "Green means go! {drv} leads them away, everyone fighting for the run into one!",
        "Lights out and away we go — and it's {drv} who edges it into the first corner!",
    ],
    "overtake": [
        "{drv} makes the move on {oth} to take P{pos}!",
        "Brilliant move! {drv} sweeps past {oth} for P{pos}!",
        "{drv} makes it stick on {oth} — that's P{pos}!",
        "{drv} gets the better of {oth} for P{pos}!",
        "{oth} had no answer there — {drv} is through into P{pos}!",
        "Lovely move from {drv} — past {oth} and up to P{pos}!",
        "{drv} sends it and completes the move on {oth} for P{pos}!",
        "Brave from {drv}! Late on the brakes and through on {oth} for P{pos}!",
        "{oth} ran a touch wide and {drv} pounced — P{pos} now!",
        "Scintillating from {drv}, that's {oth} dealt with for P{pos}!",
        "{drv} with the better exit, slingshots past {oth} into P{pos}!",
        "Wheel to wheel — and it's {drv} who comes out ahead for P{pos}!",
        "{drv} feints, {oth} bites, and the move is done — P{pos}!",
        "Clinical from {drv}! A no-nonsense pass on {oth} for P{pos}!",
        "{drv} pounces on the slightest hesitation from {oth} — P{pos}!",
        "Brilliantly judged, {drv} is through on {oth} for P{pos}!",
        "{drv} times the run to perfection and breezes past {oth} for P{pos}!",
        "{oth} defended hard but {drv} would not be denied — P{pos}!",
        "Beautifully judged from {drv} — {oth} is dispatched for P{pos}!",
        "A lunge that pays off! {drv} muscles past {oth} into P{pos}!",
        "{drv} carries more speed and sails by {oth} for P{pos}!",
        "Decisive! {drv} makes short work of {oth} to claim P{pos}!",
        "{drv} makes a brilliant move on {oth} — and that's P{pos}!",
        "Job done by {drv}, leaving {oth} for dust on the way to P{pos}!",
        "{drv} hits the slipstream perfectly and is past {oth} before they can react — P{pos}!",
        "A stunning move from {drv} — {oth} had no answer, P{pos} taken!",
        "{drv} finds the gap that barely existed and makes it work — P{pos}!",
        "The gap was there for a fraction of a second. {drv} saw it. {oth} didn't. P{pos}!",
        "Perfection. {drv} places the car exactly right, exits faster, and sails by {oth} for P{pos}!",
        "{drv} draws alongside through the previous straight and holds it all the way — P{pos}!",
        "They go side by side for the whole corner — {drv} comes out of it ahead for P{pos}!",
        "A decisive, well-judged move — {drv} past {oth} for P{pos}!",
        "No debate, no question — {drv} committed to P{pos} and claimed it from {oth}!",
        "{drv} commits, and makes it stick on {oth} for P{pos}!",
        "Superb work from {drv}, ahead of {oth} before you know it — P{pos}!",
        "A brilliantly constructed move from {drv}, using every metre of track to take P{pos} from {oth}!",
        "Pure pace advantage converted with precision — {drv} past {oth} and into P{pos}!",
        "One of the great moves of the race! {drv} past {oth}, and P{pos} is theirs!",
        "{drv} times it to perfection — a clean move on {oth} for P{pos}!",
        "They nearly collide but both hold it — and it's {drv} who emerges ahead for P{pos}!",
        "{drv} absolutely committed — and through on {oth} for P{pos}!",
        "{oth} runs deep into the corner and {drv} is immediately in the gap — P{pos} claimed!",
        "In an instant, positions have changed — {drv} takes P{pos} from {oth} in one emphatic move!",
    ],
    "overtake_long": [
        "Finally! After laps of pressure, {drv} finds a way past {oth} for P{pos}!",
        "Persistence pays — {drv} has been hounding {oth} for an age, and now takes P{pos}!",
        "The breakthrough at last! {drv} cracks {oth} and grabs P{pos}!",
        "That has been coming — {drv} wears {oth} down and snatches P{pos}!",
        "All that pressure tells! {drv} is finally through on {oth} for P{pos}!",
        "Patience rewarded! {drv} bides their time and pounces on {oth} for P{pos}!",
        "After all those looks, {drv} makes one stick on {oth} — P{pos}!",
        "The dam finally breaks — {drv} forces past {oth} for P{pos}!",
        "Relentless pressure pays off as {drv} clears {oth} at last for P{pos}!",
        "{drv} has earned this — laps of hounding {oth}, and now P{pos} is theirs!",
        "It was a question of when, not if — {drv} takes {oth} for P{pos}!",
        "Worn down at last, {oth} yields to {drv} for P{pos}!",
        "Sheer persistence from {drv} undoes {oth} — that's P{pos}!",
        "The move that's been brewing for laps — {drv} past {oth} into P{pos}!",
        "{drv} has been psychologically grinding {oth} down — and now they're through for P{pos}!",
        "An extraordinary battle — but {drv} outlasted {oth} and now leads P{pos}!",
        "Multiple corners, multiple attempts — {drv} finally breaks {oth}'s resistance for P{pos}!",
        "The mental strength of {drv} wins out — {oth} couldn't hold on forever, P{pos} taken!",
        "{drv} finds a move that {oth} simply can't cover — P{pos} after all those laps of pressure!",
        "What a battle that was — {drv} the winner, {oth} the gallant loser, P{pos} the prize!",
        "At last! The hounding, the probing, the patience — {drv} has broken through on {oth} for P{pos}!",
        "That breakthrough had to come — {drv} past {oth} and into P{pos} after a remarkable pursuit!",
        "{oth} was a brick wall for so long, but {drv} found the gap in the end — P{pos}!",
        "Inevitable in the end — {drv} had more pace and more patience; P{pos} theirs at last!",
        "A defining moment in this race — {drv} finally gets past {oth} for P{pos} in a magnificent move!",
    ],
    "retake": [
        "{drv} fights straight back past {oth} for P{pos}!",
        "And {drv} immediately returns the favour on {oth} — P{pos}!",
        "{drv} won't have that — back through on {oth} for P{pos}!",
        "A swap and a swap back — {drv} reclaims P{pos} from {oth}!",
        "No way! {drv} fires straight back past {oth} to retake P{pos}!",
        "{drv} answers immediately — back ahead of {oth} for P{pos}!",
        "What a scrap — {drv} grabs P{pos} right back off {oth}!",
        "{drv} refuses to lose the place — back ahead of {oth}, P{pos}!",
        "They trade places and {drv} comes out on top again — P{pos}!",
        "Straight back at them! {drv} retakes P{pos} from {oth}!",
        "Tit for tat at the front of this fight — {drv} back ahead of {oth} for P{pos}!",
        "{drv} says not today — repassing {oth} for P{pos}!",
        "The favour is returned instantly! {drv} back by {oth}, P{pos}!",
        "{drv} slams the door and reclaims P{pos} from {oth}!",
        "Round they go again — {drv} ahead of {oth} once more for P{pos}!",
        "{drv} had the better exit and pounces straight back — P{pos} off {oth}!",
        "Relentless from {drv} — back past {oth} for P{pos} in a flash!",
    ],
    "pass_clean": [
        "{drv} moves ahead of {oth} into P{pos}.",
        "{drv} gets the job done on {oth} for P{pos} — no fuss.",
        "That's P{pos} for {drv}, clearing {oth} cleanly.",
        "{drv} edges past {oth} and into P{pos}.",
        "Position swap there — {drv} ahead of {oth} now in P{pos}.",
        "{drv} makes the pass on {oth} stick for P{pos}.",
        "Up to P{pos} goes {drv}, with {oth} unable to respond.",
        "{drv} completes a tidy move on {oth} for P{pos}.",
        "And {drv} is by {oth} — that's P{pos} now.",
        "{drv} slots into P{pos} ahead of {oth}.",
        "Routine but well-judged — {drv} past {oth} for P{pos}.",
        "{drv} picks off {oth} and claims P{pos}.",
        "Clean as you like — {drv} is by {oth}, P{pos}.",
        "{drv} dispatches {oth} for P{pos}, no drama.",
        "Through goes {drv}, {oth} demoted to behind P{pos}.",
        "{drv} finds a way past {oth} and takes P{pos}.",
        "Job done for {drv} — clear of {oth} into P{pos}.",
        "{drv} eases ahead of {oth} to take over P{pos}.",
        "A clinical move, {drv} past {oth} for P{pos}.",
        "{drv} sweeps by {oth} and settles into P{pos}.",
    ],
    "leadchange": [
        "We have a new race leader — {drv} hits the front!",
        "{drv} is into the lead! What a moment in this race!",
        "The lead changes hands — {drv} now heads the field!",
        "And there's the move for the lead! {drv} takes it!",
        "{drv} is the new man out front — the complexion of this race has changed!",
        "A changing of the guard at the front, {drv} now leads!",
        "{drv} muscles into the lead — what a statement that is!",
        "The lead is gone! {drv} sweeps through to head the race!",
        "Brilliant! {drv} takes the lead and the crowd are on their feet!",
        "{drv} hits the front for the first time — and how they've earned it!",
        "New leader of the race: it is {drv}, and they mean business!",
        "{drv} snatches the lead — this race has been turned on its head!",
        "There goes the lead! {drv} is the man to beat now!",
        "{drv} surges into the lead — the others will have an answer to find!",
        "{drv} leads! What a moment — everything has changed at the front!",
        "P1 belongs to {drv} now — a massive turn in this race!",
        "A defining moment — {drv} goes ahead and the race is reset!",
        "Bold, decisive, brilliant — {drv} sweeps to the very front!",
        "{drv} sniffs the gap, commits, and LEADS! Sensational!",
        "Nothing stays the same in this race — {drv} goes through to lead!",
        "{drv} emerges as the new leader — can they hold on from here?",
        "P1 changes hands, and {drv} is the new name at the top!",
        "The race leader has changed — {drv}, and this contest is wide open!",
        "Lightning quick thinking from {drv} — now leading the race!",
        "This race has a new chapter — {drv} writes their name at the top!",
        "A new name at the front of the field — it's {drv}, and that is significant!",
        "The lead evaporates for the previous leader — {drv} takes command!",
        "Relentless pressure finally pays off — {drv} assumes the lead!",
        "What a race this is! {drv} is the leader, and we are nowhere near done!",
    ],
    "fastlap": [
        "{drv} lights up the timing screens — fastest lap of the race, {gap}!",
        "Purple sectors everywhere! {drv} sets the quickest lap, {gap}.",
        "A stunning lap from {drv} — {gap}, and that's the fastest so far!",
        "{drv} digs deep and bangs in the fastest lap, a {gap}!",
        "The hammer is down for {drv} — quickest lap of the race, {gap}!",
        "Sensational pace from {drv}, a new benchmark at {gap}!",
        "{drv} resets the fastest lap — {gap}, and they're flying!",
        "Top of the timing screens goes purple for {drv} — {gap}!",
        "That's mighty from {drv} — fastest lap of anyone, {gap}!",
        "{drv} finds something extra — quickest tour of the race, {gap}!",
        "A flying lap from {drv}! {gap} — nobody's been near that.",
        "The benchmark belongs to {drv} now — a blistering {gap}!",
        "{drv} throws down the gauntlet with the fastest lap, {gap}!",
        "Eye-catching speed from {drv} — {gap}, fastest of the race!",
    ],
    "spin": [
        "{drv} has spun! Drama out on track!",
        "Oh, big moment for {drv} — that's a costly mistake!",
        "{drv} loses it and tumbles down the order!",
        "Trouble for {drv}! That's going to hurt the race.",
        "Heartbreak for {drv}! Threw it all away there in one corner!",
        "{drv} is around! All that hard work undone in an instant!",
        "Snap of oversteer and {drv} is facing the wrong way!",
        "Disaster for {drv} — a spin, and they're shuffled down the field!",
        "{drv} runs wide and loses it — what a blow to their race!",
        "A half-spin for {drv}! They gather it up but lose a stack of places!",
        "Into the gravel goes {drv}! That is a hammer blow to their afternoon!",
        "{drv} caught out by the kerb — round they go, and it's all unravelling!",
        "Oh, {drv} has dropped it! A real momentum-killer, that one!",
        "Lock-up and a spin for {drv} — the front tyres simply gave up!",
        "{drv} pirouettes out of contention — agony for them!",
        "A wild moment for {drv}! Sideways, snap, and they're facing backwards!",
        "Costly, costly error from {drv} — a spin at the worst possible time!",
        "{drv} loses the rear on the exit — spun, and shuffled right down!",
        "There goes {drv}'s race! A spin, and the field streams past!",
        "Big save attempt from {drv}, but no — they've looped it!",
        "{drv} overcooks it into the corner and spins — schoolboy stuff there!",
        "Disaster strikes {drv}! Beached in the gravel and going nowhere!",
        "{drv} gets it all wrong and spirals down the order — heartbreaking!",
        "A snap of oversteer catches {drv} cold — round and round they go!",
        "{drv} clips the inside kerb and is launched into a spin!",
        "THAT is gone for {drv}! One moment, one mistake, a race changed!",
        "{drv} cannot hold it — the car spins and falls through the field!",
        "Out of nowhere, {drv} snaps into a spin — drama on track!",
        "Unbelievable! {drv} has spun! This race is not done yet!",
        "{drv} oversteers badly on the exit and pays for it with a full spin!",
        "The tyres finally said enough — {drv} in a spin and losing places fast!",
        "A brutal moment for {drv} — spun at the worst imaginable time!",
        "That spin is going to cost {drv} enormously — places lost in seconds!",
        "The rear steps out and {drv} cannot catch it — a spin and positions lost!",
        "{drv} gets into a lurid slide and round they go — dramatic moment on track!",
        "On the throttle too early and {drv} pays the ultimate price — a spin!",
        "Pressure, heat, tyres — something gave for {drv} and they've spun!",
        "An agonising moment for {drv}: a spin when everything was going so well!",
        "The circuit bit {drv} and they're now picking up the pieces of a spin!",
        "What looked like a controlled slide turns into a full-on spin for {drv}!",
    ],
    "battle": [
        "{drv} is all over the back of {oth} — a fierce scrap for P{pos}!",
        "Side by side! {drv} and {oth} going at it for P{pos}!",
        "{drv} piling the pressure on {oth} in the fight for P{pos}!",
        "{drv} has a look down the inside of {oth} — wheel to wheel for P{pos}!",
        "Glued to the gearbox of {oth}, {drv} is hunting P{pos}!",
        "What a duel this is — {drv} and {oth} trading blows for P{pos}!",
        "{drv} throwing everything at {oth} in the battle for P{pos}!",
        "Nose to tail, {drv} looking for any way past {oth} for P{pos}!",
        "The pressure is relentless from {drv} on {oth} here, P{pos} on the line!",
        "{drv} sizing up {oth} at every corner — this is for P{pos}!",
        "{drv} feints one way, then the other — {oth} doing all they can for P{pos}!",
        "This is racing at its finest — {drv} and {oth} inseparable for P{pos}!",
        "{drv} dummies {oth} into the braking zone — so close for P{pos}!",
        "They almost touched! {drv} and {oth} giving no quarter for P{pos}!",
        "{drv} draws alongside {oth} — neither willing to lift, P{pos} the prize!",
        "A proper old-fashioned scrap, {drv} versus {oth} for P{pos}!",
        "Door to door! {drv} and {oth} refuse to yield in the fight for P{pos}!",
        "{drv} has the run, {oth} slams the door — terrific stuff for P{pos}!",
        "Edge of your seat, this — {drv} hassling {oth} relentlessly for P{pos}!",
        "P{pos} is genuinely up for grabs — {drv} won't let {oth} breathe!",
        "{oth} defending superbly from {drv} — every line covered for P{pos}!",
        "Inch-perfect from both of them — P{pos} the prize in this fabulous fight!",
        "{drv} has been right in {oth}'s mirrors for two laps now — still hunting P{pos}!",
        "Brave from {drv}! Right up the inside under braking, going for P{pos}!",
        "{oth} holds the inside line and {drv} has to back out — not done yet for P{pos}!",
        "A flinch from either of them and P{pos} changes hands right there!",
        "The slipstream and then the lunge — {drv} going for it on {oth} for P{pos}!",
        "This fight for P{pos} is going to the wire — neither giving a millimetre!",
        "{drv} and {oth} swapping lines, brake markers, everything — P{pos} the only thing that matters!",
        "You'd pay double the ticket price to watch this — {drv} versus {oth} for P{pos}!",
        "Commitment from {drv} — dives to the apex, {oth} defends, P{pos} still undecided!",
        "It's a chess match, this — {drv} vs {oth}, P{pos} the king they both want!",
        "Flat-out through there and still they're level — {drv} versus {oth} for P{pos}!",
        "Mirror, signal, manoeuvre? Not for {drv} — it's all or nothing for P{pos}!",
        "{drv} and {oth}, both refusing to blink in this epic scrap for P{pos}!",
        "Can't take your eyes off this — {drv} all over {oth} for P{pos}!",
        "{drv} stays right in the tow of {oth}, setting up another attempt at P{pos}!",
        "No daylight between them — {drv} glued to {oth} in this P{pos} fight!",
        "Tenths, hundredths — that's all that separates {drv} and {oth} for P{pos}!",
        "The crowd is loving this — {drv} and {oth} wheel-to-wheel for P{pos}!",
        "Last corner? Last chance for {drv} to get past {oth} and take P{pos}!",
        "{oth} opens the door just a fraction and {drv} is immediately in the gap — P{pos}!",
        "{drv} hits the brakes impossibly late, {oth} left with nowhere to go — P{pos} the prize!",
        "Three corners, three attempts — {drv} simply will not let {oth} settle, P{pos} at stake!",
        "Physical, fierce, and totally absorbing — {drv} and {oth} for P{pos}!",
        "{drv} trying the outside line, {oth} defends the inside — P{pos} still in the balance!",
        "Absolutely no quarter given by either driver — P{pos} is worth fighting for!",
        "The gap: zero. The fight: everything — {drv} versus {oth} for P{pos}!",
        "{drv} gets a better run and here comes the attack on {oth} for P{pos}!",
        "Racing! Pure, unadulterated racing — {drv} and {oth}, P{pos} the reward!",
        "Brave as a lion, {drv}, lunging at {oth} again and again for P{pos}!",
        "Hold that line, {oth} — {drv} is THERE, P{pos} on the cusp!",
        "{oth} covers, {drv} feints, {oth} covers again — this is brilliant for P{pos}!",
        "Neither wants to give it up — {drv} and {oth} in a P{pos} battle for the ages!",
        "Millimetres between them through that chicane — {drv} hunting every gap for P{pos}!",
        "The tension is extraordinary — {drv} right there, {oth} holding on for P{pos}!",
        "That's wheel-to-wheel and then some — {drv} and {oth}, everything on the line for P{pos}!",
        "Five corners of absolute magic — {drv} on {oth}, P{pos} still up in the air!",
        "An absolute classic of a duel — {drv} won't let {oth} sleep, P{pos} the reason!",
        "{drv} at the very limit under braking — lunge for P{pos}, {oth} fights back!",
        "Every sector, every straight, every corner — {drv} probing {oth} for P{pos}!",
        "{oth} is defending heroically, but {drv} has pace — P{pos} could still change!",
        "This is what motor racing IS — {drv} versus {oth}, side by side for P{pos}!",
        "{drv} gets the tow down the straight, draws level — {oth} clinging to P{pos} under pressure!",
        "{drv} lines it up perfectly, dives under braking — {oth} has to yield for P{pos}!",
        "Breathtaking commitment from {drv} here — pushing the very limits for P{pos}!",
        "{oth} holding their nerve magnificently against the charge of {drv} for P{pos}!",
        "No team orders here — this is a proper fight, {drv} versus {oth}, P{pos} the reward!",
        "Lap after lap of relentless pressure from {drv} on {oth} — P{pos} hanging by a thread!",
        "{drv} has the faster car, {oth} has the better position — stalemate for P{pos}!",
        "Two drivers. One position. Endless drama — {drv} versus {oth} for P{pos}!",
        "The gap's at nothing — {drv} and {oth} running as one through that section for P{pos}!",
        "Neither willing to concede a single centimetre — P{pos} is everything right now!",
    ],
    # a fight that has gone the distance WITHOUT resolving — {dur} is a phrase
    # like "three laps", "the best part of a minute", or "several corners now".
    "battle_sustained": [
        "{drv} has been glued to the back of {oth} for {dur} now — and still can't find a way past for P{pos}.",
        "This battle for P{pos} has raged for {dur} — {drv} relentless, {oth} refusing to crack.",
        "{dur} of pure pressure: {drv} all over {oth}, the gap never more than a tenth — P{pos} still unresolved.",
        "They've been nose-to-tail for {dur}, {drv} and {oth} — something has to give in this fight for P{pos}.",
        "Credit to {oth} — under siege from {drv} for {dur} now and still holding P{pos}.",
        "{drv} has thrown everything at {oth} for {dur} — every corner, every braking zone — but P{pos} stays put.",
        "For {dur} these two have been inseparable — {drv} hunting, {oth} defending, P{pos} the prize.",
        "What a war of attrition for P{pos} — {drv} and {oth} locked together for {dur} and counting.",
        "{oth} has had {drv} filling the mirrors for {dur} straight — and P{pos} is still anybody's.",
        "It's been {dur} of this now — {drv} probing, {oth} covering — a magnificent scrap for P{pos}.",
        "Relentless from {drv} — {dur} spent chasing {oth} down, and still no gap for P{pos}.",
        "The defining battle of the race: {drv} versus {oth} for P{pos}, unbroken for {dur} now.",
    ],
    "pit": [
        "{drv} peels off into the pit lane.",
        "And {drv} comes in for service — a key moment in their race.",
        "{drv} dives into the pits, the crew ready and waiting.",
        "In comes {drv} — the timing of this stop could be crucial.",
        "{drv} surrenders track position for fresh rubber.",
        "Box, box for {drv} — the crew spring into action.",
        "{drv} ducks into the pits — let's see how the undercut plays out.",
        "Service time for {drv}, and every second in that pit box counts.",
        "{drv} commits to the stop — a gamble that could make their race.",
        "Down pit lane comes {drv}, looking for that fresh-tyre advantage.",
    ],
    "lastlap": [
        "Last lap! {drv} leads the field onto the final tour!",
        "This is it — the final lap, and {drv} is out in front!",
        "The white flag is out — one lap to settle it, {drv} ahead!",
        "Final lap! Can {drv} hold on to bring it home?",
        "One lap remains, and {drv} leads — nerves of steel required now!",
        "Here we go — the last lap, {drv} out front and the pressure cranked up!",
        "The bell lap! {drv} just needs to keep it on the island!",
        "Final tour of {trk} — {drv} can almost smell the chequered flag!",
        "Last lap drama beckons — {drv} leads, but it's not over yet!",
        "This is the one that counts — {drv} heads onto the final lap!",
    ],
    "win": [
        "{drv} takes the win! A superb drive from start to finish!",
        "It's {drv}! The chequered flag falls and {drv} is your winner!",
        "Victory for {drv}! What a performance here at {trk}!",
        "{drv} crosses the line to win it! Sensational stuff!",
        "And {drv} does it! The chequered flag, and a brilliant victory!",
        "The win goes to {drv} — controlled, composed, and utterly deserved!",
        "{drv} wins it at {trk}! They have been the class of the field all day!",
        "The flag falls for {drv} — a flawless drive rewarded with victory!",
        "Job done for {drv}! A win that's been on the cards since lights out!",
        "{drv} seals the win! What a way to cap off the afternoon!",
        "Glory for {drv} at {trk} — they timed that race to perfection!",
        "{drv} is the winner! Arms aloft, and richly deserved too!",
        "And it's {drv} who takes the spoils — a commanding victory!",
        "{drv} crosses the line first — pure class from start to finish!",
    ],
    "second": [
        "{drv} brings it home in second — a fine result.",
        "Second place for {drv}, right in the mix all afternoon.",
        "{drv} takes the runner-up spot, and won't be too disappointed with that.",
        "A strong second for {drv} — they pushed the winner all the way.",
        "{drv} settles for second, but what a drive it's been.",
        "The runner-up is {drv} — so close to the win, but a great result.",
        "Second across the line, {drv} — they gave it everything.",
        "{drv} claims second place, a thoroughly earned piece of silverware.",
        "P2 for {drv}, and they'll feel they had the pace to win on another day.",
        "{drv} takes the chequered flag in second — a job well done.",
    ],
    "third": [
        "And {drv} completes the podium in third!",
        "Third place and the final podium step goes to {drv}.",
        "{drv} rounds out the top three — a well-earned podium.",
        "{drv} hangs on for third — a podium they fought hard for.",
        "The final step belongs to {drv} — third, and delighted with it.",
        "{drv} grabs the last podium spot — what a battle that was for third.",
        "Third across the line, {drv} — champagne for them today.",
        "{drv} secures the bronze — a fine afternoon's work.",
        "P3 for {drv}, and they've earned every bit of that podium.",
        "{drv} completes the rostrum — third place and smiles all round.",
    ],
    "summary": [
        "What a thrilling race here at {trk}! Congratulations to {p1} on the win, "
        "with {p2} and {p3} completing the podium.",
        "A cracking race from start to finish! {p1} the winner, ahead of {p2} and "
        "{p3} — a brilliant top three.",
        "That's the chequered flag on a superb race! {p1} takes it, {p2} second and "
        "{p3} third. Hats off to all three.",
        "A race to remember at {trk}! {p1} stands on the top step, joined by {p2} "
        "and {p3} — thoroughly deserved, the lot of them.",
        "And that's the flag! {p1} the winner here at {trk}, {p2} second, {p3} "
        "third — a podium they can all be proud of.",
        "What a contest that was! Victory {p1}, then {p2}, then {p3} — three drivers "
        "who left it all out on track.",
        "The dust settles at {trk} — {p1} takes the win from {p2} and {p3}. "
        "Cracking entertainment from lights to flag.",
        "A worthy winner in {p1}, backed up by {p2} and {p3} on the rostrum. "
        "That, ladies and gentlemen, was a race.",
        "{p1} the deserved victor at {trk}, {p2} and {p3} completing a fine top "
        "three. We've been spoiled today.",
    ],
    # CLOSING SIGN-OFF — the very last thing the booth says. After this, audio
    # stops: the broadcast is over. Always commentator-voiced, warm and final.
    "signoff": [
        "That's all from us here at {trk}. Join me and {pundit} next time on RacerTV for the next event — goodbye for now!",
        "From {comm} and {pundit}, that's the end of our coverage at {trk}. Join us next time on RacerTV — take care!",
        "We'll leave it there from {trk}. Join me and {pundit} next time on RacerTV for all the action. Goodbye!",
        "That wraps up RacerTV's coverage here at {trk}. Be sure to join {comm} and {pundit} again next time. So long!",
        "And on that note, we say goodbye from {trk}. Join me and {pundit} next time on RacerTV — until then, cheers!",
        "That's the chequered flag on our broadcast. From all of us at RacerTV, join us next time for the next event. Goodbye!",
        "Our work here is done at {trk}. Join me and {pundit} next time on RacerTV — thanks for watching, goodbye!",
    ],
    # CLIMACTIC VICTORY SIGN-OFF — the signature closing call, naming the winner
    # and the venue with a flourish, then the RacerTV sign-off. Used as the very
    # last line of the race wrap (a win earns a bigger send-off than the plain
    # signoff). {p1} = winner, {trk} = circuit.
    "victory_signoff": [
        "And there it is — {p1} crosses the line to take victory here at {trk}! A worthy winner if ever there was one. From {comm} and {pundit}, join us next time on RacerTV. Goodbye!",
        "{p1} takes the chequered flag and the win at {trk} — the end of a cracking race! That's all from {comm} and {pundit}. Join us next time, here on RacerTV. So long!",
        "So {p1} seals victory at {trk}, capping a superb afternoon's racing! From all of us at RacerTV, thanks for watching — and we'll see you next time. Goodbye!",
        "Victory belongs to {p1} here at {trk} — a brilliant drive from lights to flag! That wraps up our coverage. Join {comm} and {pundit} next time on RacerTV. Cheers!",
        "And {p1} does it — across the line to win at {trk}, the perfect end to the race! From me, {comm}, and {pundit}, that's goodbye from RacerTV. Until next time!",
        "{p1} crosses the line to take a famous victory at {trk}! What a way to finish. From {comm} and {pundit}, join us again next time on RacerTV — goodbye for now!",
    ],
    "lap_milestone": [
        "We're on lap {lap} of {total} here at {trk}.",
        "Lap {lap} of {total} — and the race continues to unfold.",
        "{togo} laps remaining now — the tension is building.",
        "Just {togo} laps to go — this is where it gets decided.",
        "Into the closing stages, {togo} laps left on the board.",
        "Lap {lap} of {total}, and there's still plenty to play for.",
        "We've reached lap {lap} of {total} — the race entering a new phase.",
        "Past half-distance now, lap {lap} of {total} on the board.",
        "{togo} to go, and the strategies are starting to reveal themselves.",
        "Lap {lap} here at {trk} — settling into the rhythm of the race.",
        "Only {togo} laps left now — decision time is approaching.",
        "The board shows lap {lap} of {total} — squeeze every lap counts now.",
        "{togo} laps remaining and the tension cranks up another notch.",
        "Lap {lap} of {total} — and the picture is far from settled.",
        "We tick onto lap {lap} — {togo} still to run at {trk}.",
        "Into lap {lap} of {total}, and the racing shows no sign of easing.",
    ],
    # TIMED race — the clock winding down. {mins} = "5 minutes" / "1 minute".
    "time_remaining": [
        "{mins} to go on the clock here at {trk}!",
        "Just {mins} remaining — the timer is the enemy now!",
        "We're down to {mins} left in this one!",
        "Under {mins} to run — the clock ticking towards zero!",
        "{mins} on the clock, and the pressure is cranking up!",
        "Into the final {mins} — whatever's going to happen, it happens now!",
        "The clock shows {mins} remaining — decision time at {trk}!",
        "{mins} left, and every second counts from here!",
    ],
    "standings": [
        "As it stands, {p1} leads from {p2} and {p3}.",
        "Your top three at the moment: {p1}, {p2}, and {p3}.",
        "{p1} out in front, {p2} and {p3} giving chase.",
        "The order up front: {p1}, then {p2}, with {p3} third.",
        "{p1} setting the pace, {p2} and {p3} the closest pursuers.",
        "At the sharp end it's {p1}, {p2} and {p3} as things stand.",
        "Leading the way, {p1} — with {p2} and {p3} completing the top three.",
        "{p1} controls it from {p2}, {p3} hanging on in third.",
        "Reminder of the order: {p1} leads {p2}, {p3} third.",
        "{p1} heads the field, {p2} shadowing in second, {p3} third.",
        "Top of the timing screen: {p1}, {p2}, {p3} — your provisional podium.",
        "It's {p1} from {p2} and {p3} as we stand — a fascinating top three.",
        "Out front {p1}, then daylight, then {p2} and {p3} scrapping away.",
        "Your leaders: {p1}, {p2} and {p3} — and plenty still to come.",
        "{p1} in command, {p2} hunting, {p3} clinging to that final podium spot.",
        "The order at the front reads {p1}, {p2}, {p3} right now.",
        "{p1} leads the way from {p2}, with {p3} completing the trio.",
        "The race shaping up nicely — {p1} out front, {p2} second, {p3} third.",
        "{p1} the leader, {p2} the hunter, {p3} hanging on in the final podium spot.",
        "So the running order: {p1}, {p2}, {p3} — and it's not done yet.",
        "Three drivers out front: {p1}, {p2}, {p3} — the podium in embryo.",
        "Just to remind you, we have {p1} leading {p2} with {p3} third.",
        "{p1} controlling the race, {p2} waiting, {p3} watching from third.",
        "Check the top three — {p1} holds sway, {p2} and {p3} keep the pressure on.",
        "In terms of the race order: {p1} P1, {p2} P2, {p3} P3.",
        "It's an ordered race at the top — {p1} from {p2} from {p3}.",
        "{p1} hasn't put a foot wrong up front, {p2} and {p3} keeping honest.",
        "{p1} with the race in hand, {p2} and {p3} looking for any chink.",
        "The podium could look like this at the end — {p1}, {p2}, {p3}.",
        "Quiet at the front? No — {p1} still working hard to stay ahead of {p2} and {p3}.",
        "Unchanged up front: {p1}, {p2}, {p3} — though that could flip at any moment.",
        "Three drivers, three spots, one race — {p1} leads {p2} and {p3}.",
        "The running order stays: {p1} ahead, {p2} threatening, {p3} completing the trio.",
        "P1: {p1}. P2: {p2}. P3: {p3}. And a lot of racing still to go.",
        "{p1} comfortable up front for now, {p2} lurking, {p3} circling.",
        "Short version: {p1} leads, {p2} chases, {p3} hangs on.",
        "A clean top three — {p1}, {p2}, {p3} — though clean can become chaos in a heartbeat.",
        "Nothing between the intentions — {p1} wants to win, {p2} and {p3} want to stop that.",
        "{p1} the name at the top, {p2} and {p3} doing everything to change that.",
        "That's {p1} controlling things, {p2} waiting for a mistake, {p3} an eye on second.",
        "In the order: {p1}, then {p2}, then {p3} — a snapshot that could shift.",
        "Three-way spread at the top — {p1} leads {p2} and {p3} right now.",
        "{p1} is your race leader, {p2} your main challenger, {p3} your other podium contender.",
        "Freeze the frame and it's {p1} ahead, {p2} behind, {p3} in third. For now.",
        "Nothing settled yet — {p1} first, {p2} second, {p3} third, all capable of more.",
        "The board shows {p1}, {p2}, {p3} — any of those three could yet win this.",
        "{p1} sets the tone, {p2} and {p3} must react — that's where we are.",
        "Order at the front: {p1} is your leader, {p2} makes up second, {p3} rounds it out.",
        "{p1} heading the field, {p2} in tow, {p3} just behind — a tight front three.",
    ],
    "car": [
        "{drv} doing all this aboard the {car} — a lovely bit of kit.",
        "Worth remembering {drv} is wrestling the {car} round here.",
        "That {car} in the hands of {drv} looks right at home.",
        "The {car} suits this circuit, and {drv} is making it sing.",
        "{drv} getting everything out of the {car} today.",
        "Plenty of pace in that {car} — {drv} extracting all of it.",
        "You can hear that {car} working hard underneath {drv}.",
        "A real challenge taming the {car}, but {drv} is on top of it.",
        "The {car} has been a weapon in {drv}'s hands all afternoon.",
        "{drv} clearly relishing the balance of that {car} today.",
        "You don't often see a {car} driven quite like {drv} is driving it.",
        "That {car} sounds glorious as {drv} winds it out of the corners.",
        "{drv} and the {car} — a partnership that's really come alive here.",
        "Whatever they've done to that {car}, {drv} is reaping the rewards.",
        "The {car} looks a handful, but {drv} is making it dance.",
    ],
    "closing": [
        "{drv} is reeling in {oth} — the gap is coming down fast!",
        "{drv} has the bit between the teeth, closing right onto {oth}!",
        "Here comes {drv}! Catching {oth} hand over fist for P{pos}!",
        "The gap is tumbling — {drv} is all over {oth} now for P{pos}!",
        "{drv} has found a second wind, hunting down {oth} for P{pos}!",
        "Chunks of time coming out of it — {drv} closing on {oth} for P{pos}!",
        "{oth} had better look in the mirrors — {drv} is coming for P{pos}!",
        "{drv} is on a charge, eating into the gap to {oth} every lap!",
        "Like a heat-seeker, {drv} closing right down on {oth} for P{pos}!",
        "The elastic is snapping back — {drv} closing fast on {oth}!",
        "{drv} sniffs a chance — closing right onto the gearbox of {oth}!",
        "A few tenths shaved every lap — {drv} will be all over {oth} shortly for P{pos}!",
        "The gap was comfortable; it is no longer — {drv} is coming at {oth} for P{pos}!",
        "P{pos} could be about to change hands — {drv} hunting {oth} down!",
        "{oth} will be able to see {drv} in the mirrors very soon now — P{pos} in danger!",
        "{drv} smells an opportunity and is going for it — the gap to {oth} evaporating!",
        "A fightback from {drv}! Eating into {oth}'s advantage for P{pos} lap by lap!",
        "Look at those splits — {drv} is quickest on track, and {oth} will know it for P{pos}!",
        "The momentum has swung — {drv} now the hunter, {oth} the hunted for P{pos}!",
        "{drv} setting purple sectors, {oth} looking nervous — P{pos} under serious threat!",
        "A telling moment — {drv} closing the gap to {oth}, and P{pos} could be next!",
        "{oth} is fighting the tyres, {drv} has the bit between the teeth — P{pos} will flip!",
        "It's cat and mouse, and right now {drv} is very much the cat after P{pos}!",
        "Every lap, {drv} is taking a little more time out of {oth} — P{pos} the prize!",
        "The trajectory is clear — {drv} is coming, {oth} must respond or lose P{pos}!",
        "A determined charge from {drv}, carving through the air toward {oth} for P{pos}!",
        "Less than a second now — {drv} right on the limit, closing fast on {oth} for P{pos}!",
        "What a run this is from {drv} — systematically pulling {oth} back for P{pos}!",
        "{drv} is making the gap look like a suggestion — closing on {oth} for P{pos}!",
        "{oth} has to find something extra — {drv} is relentless in pursuit of P{pos}!",
    ],
    "pulling_away": [
        "{drv} is stretching the legs out front — {gap} the lead now.",
        "{drv} pulling clear at the front, breaking the elastic to {gap}.",
        "Out in front, {drv} is in a race of their own, {gap} clear.",
        "{drv} is disappearing up the road — {gap} and growing.",
        "No catching {drv} at this rate — the lead is out to {gap}.",
        "{drv} flexing the muscles out front, easing clear to {gap}.",
        "A race of one for {drv}, who has stretched it to {gap}.",
        "{drv} simply has more, edging the advantage out to {gap}.",
        "The lead is becoming commanding — {drv} now {gap} to the good.",
        "{drv} controls it beautifully from the front, {gap} in hand.",
        "The gap is growing with every lap — {drv} building a cushion of {gap}.",
        "{drv} with daylight — {gap} clear and seemingly able to manage it.",
        "A serene pace-setter, {drv}, who has extended the advantage to {gap}.",
        "{drv} running their own race at the front — {gap} and not yet at the limit.",
        "The field is being left behind — {drv} with {gap} and cruising.",
        "{drv} lapping at will — the advantage has grown to {gap} with ease.",
        "A statement of intent from {drv} — {gap} the lead, and looking comfortable.",
        "{drv} pacing themselves perfectly and the gap keeps growing — {gap} now.",
        "Metronomic, {drv} — lap after lap pulling clear to {gap}.",
        "No drama at the front — {drv} with {gap} and managing it to perfection.",
        "The gap tells the story — {drv} has simply gone to another level, {gap} clear.",
        "{drv} has the engine turned down and is STILL extending the lead to {gap}.",
        "A controlling performance from {drv}, who now has {gap} to play with.",
        "At this rate the rest are racing for second — {drv} has {gap} in hand.",
        "{drv} with a growing margin — {gap} now, and that's not the final number.",
    ],
    "recovery": [
        "What a charge from {drv} — up to P{pos} now from way back!",
        "{drv} is carving through the field, into P{pos}!",
        "Brilliant recovery drive from {drv}, now up to P{pos}!",
        "{drv} on the move again — sliced up to P{pos} from nowhere!",
        "A storming comeback from {drv}, now all the way up to P{pos}!",
        "{drv} is the comeback story of the race — into P{pos}!",
        "Scything through them, {drv} — up to P{pos} and still climbing!",
        "What a fightback! {drv} drags it up to P{pos}!",
        "{drv} refuses to give in — recovered to P{pos} now!",
        "Pass after pass for {drv} — up into P{pos}, sensational stuff!",
        "The comeback is ON — {drv} now into P{pos} and hunting more!",
        "Count them back in — {drv} is at P{pos} and this story isn't over!",
        "From the back to P{pos} — {drv} putting on a driving master class!",
        "Place by place, corner by corner — {drv} now at P{pos}, still going forward!",
        "Don't write off {drv} — already up to P{pos} and with plenty of fight left!",
        "{drv} treating this like a sprint race — charging to P{pos} with intent!",
        "A charge nobody expected — {drv} all the way up to P{pos}!",
        "This is how you respond — {drv} on a stunning recovery to P{pos}!",
        "The heart of a competitor — {drv} dragging themselves up to P{pos}!",
        "Relentless from {drv} — another place gained, now at P{pos}!",
    ],
    "podium_lock": [
        "As it stands, that's your provisional podium taking shape!",
        "The top three beginning to settle as we head for the flag!",
        "Barring drama, that looks like your podium right there!",
        "The rostrum positions are firming up as the laps tick down!",
        "Unless something changes, those are your three podium men!",
        "The top three are pulling clear — a podium order emerging!",
        "It's starting to look settled at the sharp end for the podium!",
        "Those three look to have the podium between them now!",
    ],
    "penalty": [
        "Penalty for {drv}! The stewards have taken a dim view of that.",
        "{drv} has been handed a penalty — that could be costly.",
        "Trouble with the stewards for {drv} — a penalty incoming.",
        "The stewards are not happy — a penalty for {drv}.",
        "{drv} will have to serve a penalty — a real blow to their race.",
        "That's a penalty for {drv}, and it could undo all their hard work.",
        "Under investigation no more — {drv} gets the penalty.",
        "Costly, this — {drv} penalised, and the gap they built now wiped out.",
        "{drv} pays the price with the stewards — penalty applied.",
        "A time penalty for {drv} — that reshuffles things nicely.",
    ],
    "yellow": [
        "Yellow flags are out! Caution on track — slow down through there.",
        "We've got yellow flags waving — there's an incident trackside.",
        "Yellows out! The drivers need to back off through this sector.",
        "Caution flags flying — something has happened up ahead.",
        "Yellow flags in that sector — no overtaking through there now.",
        "Hold station — yellows are out and there's a car in trouble.",
        "The marshals are waving yellow — drivers easing off through there.",
        "Double waved yellows — this is a serious one, big caution.",
        "Yellow flags interrupt the racing — everyone backing off now.",
        "Incident on track, yellows out — keep it sensible through here.",
    ],
    "battle_mid": [
        "Great scrap in the midfield — {drv} hounding {oth} for P{pos}!",
        "Plenty going on down the order, {drv} pressuring {oth} for P{pos}!",
        "Don't forget the midfield — {drv} all over {oth} for P{pos}!",
        "Lower down, {drv} is throwing the kitchen sink at {oth} for P{pos}!",
        "A lovely tussle in the pack, {drv} versus {oth} for P{pos}!",
        "The midfield is alight — {drv} hassling {oth} for P{pos}!",
        "Some of the best racing is in the pack — {drv} on {oth} for P{pos}!",
        "{drv} and {oth} trading paint in the midfield for P{pos}!",
        "Forget the front — {drv} versus {oth} for P{pos} is the one to watch!",
        "In among the pack, {drv} simply will not let {oth} settle, P{pos} at stake!",
        "{drv} has been glued to {oth} for laps now in the fight for P{pos}!",
        "Cracking midfield duel, {drv} desperate to find a way by {oth} for P{pos}!",
        "{drv} keeps probing {oth} — this midfield battle for P{pos} is terrific!",
        "Lower down the order it's no less fierce — {drv} on {oth} for P{pos}!",
        "{drv} senses weakness in {oth} — turning the screw for P{pos}!",
        "A battle raging in the midfield — {drv} is right up {oth}'s exhaust for P{pos}!",
        "Midpack magic — {drv} throwing move after move at {oth} for P{pos}!",
        "The front might be stable but here {drv} is doing anything but — P{pos} the mission!",
        "{drv} taking the long way round, hunting {oth} every lap for P{pos}!",
        "Two drivers who absolutely refuse to let this settle — {drv} versus {oth} for P{pos}!",
        "The race within the race — {drv} and {oth} grinding it out for P{pos}!",
        "Points on the line in the midfield too — {drv} won't give {oth} a moment's peace for P{pos}!",
        "Every lap a new attempt — {drv} relentless in hunting down {oth} for P{pos}!",
        "{oth} is defending every inch of P{pos}, but {drv} is not going away!",
        "Drama everywhere — {drv} going wheel-to-wheel with {oth} for P{pos} down the pack!",
        "Midfield brawl — {drv} and {oth} have been at it for laps, P{pos} the prize!",
        "{drv} on a different tyre strategy? Whatever it is, they are ALL over {oth} for P{pos}!",
        "A real scrap among the pack — {drv} and {oth} making this midfield exciting for P{pos}!",
        "Nobody's conceding P{pos} easily — {drv} really making {oth} work for it!",
        "Brilliant racing further down the order — {drv} and {oth} genuinely excellent for P{pos}!",
        "Two drivers who clearly want P{pos} very badly — and it shows!",
        "{drv} making the most of every straight, every braking zone, every gap — {oth} for P{pos}!",
        "A close-fought, hotly contested battle in the midfield — {drv} versus {oth}, P{pos} up for grabs!",
        "They're going to touch if this keeps up — {drv} and {oth} are THAT close for P{pos}!",
        "The midfield is no place for the faint-hearted — {drv} and {oth} proving that for P{pos}!",
        "Inch-perfect racing in the pack — {drv} on {oth}, P{pos} the only thing that matters!",
    ],
    # the lead asks the pundit to recap a specific driver's race (the pundit then
    # answers dynamically from the RACE STORY data). {drv} = driver, {pundit}=name
    "driverstory_q": [
        "So {pundit}, how's {drv}'s race panned out?",
        "{pundit}, talk us through {drv}'s race so far.",
        "What's the story of {drv}'s afternoon been, {pundit}?",
        "How would you sum up {drv}'s race, {pundit}?",
        "{pundit}, give us the picture on {drv}'s race.",
        "Where's it all gone for {drv} today, {pundit}?",
        "Bring us up to speed on {drv}'s race, {pundit}.",
        "{pundit}, what's been happening for {drv} out there?",
        "How's the day unfolded for {drv}, {pundit}?",
        "Run me through {drv}'s race to this point, {pundit}.",
        "{pundit}, how would you describe {drv}'s afternoon so far?",
        "What's {drv}'s race been like from where you're sitting, {pundit}?",
        "Paint us the picture of {drv}'s race, {pundit}.",
        "{pundit}, what's the journey been for {drv} today?",
    ],
    "crosstalk_q": [
        "{pundit}, how do you think {drv} is shaping up this race?",
        "What do you make of {drv}'s pace out there, {pundit}?",
        "Over to you, {pundit} — what's catching your eye?",
        "{pundit}, talk me through what's happening up front.",
        "How do you think {drv} is shaping up this race?",
        "What do you make of {drv}'s pace out there?",
        "{drv} up in P{pos} — are you impressed with that?",
        "Talk me through {drv}'s race so far, then.",
        "Is {drv} the real deal today, do you think?",
        "Where's this race being won and lost for you?",
        "What's caught your eye out there so far?",
        "Can anyone live with {drv} at this rate?",
        "Is {drv} managing those tyres well enough for you?",
        "What's the key to this race from here, do you reckon?",
        "Are we set for a grandstand finish here?",
        "Who's the standout performer for you so far?",
        "Has {drv} got enough in hand to hold on, do you think?",
        "What would you be telling {drv} on the radio right now?",
        "Is the pressure starting to tell on {drv}, do you think?",
        "Strategically, where does this race get decided for you?",
        "Are the tyres going to be the story of this race?",
        "Who's quietly having the best race that nobody's talking about?",
        "Does {drv} have the racecraft to make P{pos} count from here?",
        "What's your read on the battle for the podium?",
        "Is there a move on the cards for {drv}, do you reckon?",
        "How would you rate {drv}'s afternoon so far out of ten?",
        "Are we watching the drive of the day from {drv} here?",
        "What's the one thing you'd change if you were on {drv}'s pit wall?",
        "Can {drv} convert that pace into a result, in your view?",
        "Is this a vintage performance from {drv}, or is there more to come?",
        "Where do you see this one finishing up, then?",
    ],
    # LORE — booth backstory banter. MILES CRAWFORD (lead) was a Formula One
    # WORLD CHAMPION who raced Schumacher, Barrichello and Häkkinen, then went
    # rallying later in his career. BRETT CALLOWAY (pundit) is a Le Mans / WEC
    # champion who battled the endurance greats (Kristensen, McNish, Pirro,
    # Lotterer, Capello). Track-SPECIFIC memories come from LORE_*_BY_TRACK via
    # _lore_answer; these generic pools (named with {trk}) are the fallback.
    # lore_q = Miles asks Brett about his WEC past -> lore_a (Brett answers).
    "lore_q": [
        "{pundit}, you've won Le Mans, battled the endurance greats — what does a place like {trk} ask of a driver?",
        "You raced prototypes against Kristensen and McNish, {pundit}. Where's the lap really won at {trk}?",
        "Drawing on all those Le Mans years, {pundit} — how would you be attacking {trk}?",
        "{pundit}, with a Le Mans crown to your name, how does this lot compare to the WEC legends you raced?",
        "Take us back, {pundit} — you raced the endurance era's very best. What's the trick to {trk}?",
        "You've felt {trk} at the limit in a prototype, {pundit}. What separates the quick from the rest here?",
        "{pundit}, from one champion to a room full of hopefuls — what's the secret this circuit demands?",
    ],
    "lore_a": [
        "{trk}? I raced sportscars at places like this in my Le Mans years — wheel to wheel with Tom Kristensen more times than I can count. Endurance teaches patience, and that wins here too.",
        "In my WEC days I'd be three hours into a stint somewhere like {trk}, Allan McNish glued to my gearbox. You learn to be fast AND kind to the car — that's the whole secret.",
        "I won my share against the endurance greats — Kristensen, Pirro, McNish — and {trk} rewards the very same things: rhythm, respect, and saving the car for when it matters.",
        "We didn't have all this telemetry in my prototype days — you felt it through the seat. Battling Lotterer through corners like these, you drove on instinct alone.",
        "One of my best ever drives came at a circuit much like {trk} — Dindo Capello and I refusing to lift, two cars as one. Commit, trust it, never lift when your gut says lift.",
        "The greats I raced never forced it — Kristensen was smoothest of the lot, never fighting the car. These youngsters could learn a thing or two from that.",
    ],
    # lore_q_rally = Brett asks Miles about his F1-champion-then-rally past ->
    # lore_a_rally (Miles answers). (Key kept for engine compatibility.)
    "lore_q_rally": [
        "{comm}, you were World Champion before you ever went rallying — bet you saw a few things at a place like {trk}?",
        "You raced Schumacher and Häkkinen for a title, {comm}. Does this lot have what those greats had?",
        "{comm}, F1 champion turned rally man — what does {trk} take, in your book?",
        "You've battled the very best wheel to wheel, {comm}, then gone sideways through the forests. Do these drivers impress you?",
        "From a world title to the rally stages, {comm} — how would you be tackling {trk}?",
    ],
    "lore_a_rally": [
        "{trk}? I won races at places like this in my Formula One days — wheel to wheel with Schumacher and Häkkinen, no lifting, no quarter. Then I went rallying and learned car control all over again!",
        "In my championship year I'd attack a circuit like {trk} flat out, Rubens Barrichello filling my mirrors the whole way. Later, in rally, I learned the limit's a feeling — and the best here drive on that feeling.",
        "I took my F1 title scrapping with the very best — Mika, Michael, Rubens — at tracks like {trk}. Then the forests humbled me all over again. Car control is car control, wherever you race.",
        "Ha! After a world championship, throwing a rally car blind over a crest taught me real humility. {trk} rewards that same bravery — commit, and trust it.",
        "I raced Häkkinen for a title down to the last round — ice in the veins, neither of us lifting. That's what {trk} demands of these drivers too, if they want it.",
    ],
    "stat": [
        "{p1} leads {p2} by {gap} at the front.",
        "Just {gap} covers {drv} and {oth} as they scrap it out.",
        "The fastest lap of the race so far: {drv}, a {time}.",
        "{drv} has made up real ground — up to P{pos} now.",
        "{gap} the gap as {drv} chases down {oth}.",
        "Steady at the front, {p1} holding {gap} over {p2}.",
        "{drv} now up to P{pos} — a gain of real significance.",
        "The margin is down to {gap} between {drv} and {oth}.",
        "{p1} has eased the gap to {p2} out to {gap}.",
        "Half a second here, a tenth there — {gap} now covers this fight.",
        "{drv} sitting pretty in P{pos}, with {gap} of breathing room.",
        "The numbers tell the story — {gap} between the top two.",
        "{drv} has clawed back to within {gap} of {oth}.",
        "Quickest of all out there: {drv}, with a {time}.",
        "That gap of {gap} is the difference between P{pos} and the place behind.",
    ],
    "praise": [
        "Watch {drv} here — beautifully smooth, looking after the tyres a treat.",
        "{drv} is in complete control, not putting a wheel wrong.",
        "Lovely commitment from {drv}, a textbook racing line through there.",
        "Metronomic, {drv} — every lap looks identical, supremely consistent.",
        "The car looks planted under {drv}, real confidence on display.",
        "Gorgeous car placement from {drv}, using every last inch of the circuit.",
        "{drv} making it look effortless out there — so composed.",
        "Beautiful balance from {drv}, carrying serious speed through the quick stuff.",
        "{drv} is driving with the maturity of a veteran out there.",
        "Just look at {drv}'s minimum speeds — clinical through the corners.",
        "{drv} hooking up every apex, a joy to watch this.",
        "Ice in the veins from {drv}, totally unflustered under pressure.",
        "{drv} is dancing on the very limit but never crossing it.",
        "That's a masterclass in tyre conservation from {drv}.",
        "{drv} threading the needle through the chicane — sublime precision.",
        "Not a wasted movement from {drv}, economy and speed in perfect harmony.",
        "{drv} carrying the speed of a qualifying lap, race after race.",
        "Textbook from {drv} — brake, turn, settle, fire out. Beautiful.",
        "{drv} is making the rest look ordinary out there.",
        "Such soft hands from {drv}, the car never unsettled for a moment.",
        "{drv} living right on the edge of grip and loving every second.",
        "A clinic in racecraft from {drv} — measured, mature, mighty quick.",
        "{drv} putting it exactly where they want it, lap after lap.",
        "You can set your watch by {drv} — relentless consistency.",
        "{drv} attacking the kerbs with total confidence and control.",
        "The smoothest car on track belongs to {drv} right now.",
        "{drv} extracting every ounce of performance — a treat to watch.",
        "Faultless from {drv} — pressure simply does not register.",
        "{drv} flowing through the esses like water — gorgeous to behold.",
        "The chassis is alive under {drv} — you can feel the communication through the wheel.",
        "{drv} reading every moment before it happens — racing intelligence at its finest.",
        "A drive of rare quality from {drv} — unhurried, unflustered, unstoppable.",
        "{drv} is simply on a different level today — nobody else is doing THAT.",
        "Quick and clinical — {drv} giving a genuine lesson in how to race.",
        "{drv} has total command of that machinery — a pleasure to watch.",
        "No drama, no mistakes, no wasted movement — {drv} in a perfect groove.",
        "{drv} threading those exits with pinpoint precision — the car is a missile.",
        "Incredible spatial awareness from {drv} — every centimetre of road used.",
        "The tyre management has been exceptional from {drv} — they've got so much left.",
        "{drv} running a race two seconds ahead of everyone else in their mind.",
        "Genius brake balance adjustments from {drv} — adapting to everything the track throws.",
        "The late braking from {drv} is absolutely savage — yet the car stays perfectly balanced.",
        "{drv} is the complete package right now — speed, control, racecraft — all there.",
        "Look at that exit speed from {drv} — the rear is fully planted and they just fly.",
        "{drv} finding time where nobody else can — a driver truly in the zone.",
        "Not a tenth wasted, not a centimetre wasted — {drv} is in the flow.",
        "{drv} making those tyres last an eternity — the softs still alive and well.",
        "What a performance — {drv} is one of the best drivers on this grid and showing it.",
        "The body language of the car tells you everything — {drv} completely in control.",
    ],
    # story-callback variants for praise — used when the driver had a notable event
    "praise_led": [
        "{drv} showing exactly why they led earlier — back in magnificent form.",
        "Class will always tell — {drv} at the front of the group in scintillating form.",
        "{drv} proving they belong at the sharp end — utterly dominant in that sector.",
        "Leadership quality on display from {drv} — every lap a statement.",
        "{drv} with the air of a race leader even running here — quality shining through.",
    ],
    "praise_recovery": [
        "{drv} showing incredible resilience — composure rebuilt, the pace is back.",
        "What a turnaround from {drv} — after the troubles earlier, now driving beautifully.",
        "{drv} refusing to let that earlier moment define the race — quality recovery.",
        "Character study: {drv} bouncing back with a drive of genuine class.",
        "The mark of a great driver — {drv} pulling it all back together after the earlier drama.",
    ],
    "midpack": [
        "A steady, unspectacular run for {drv} in P{pos}.",
        "{drv} holding station in P{pos} — solid if unremarkable.",
        "Quietly competent from {drv}, keeping it clean in P{pos}.",
        "{drv} doing a tidy job in P{pos}, out of trouble.",
        "Not setting the world alight, but {drv} is banking a result in P{pos}.",
        "{drv} sitting in no-man's-land in P{pos}, just managing the race.",
        "An anonymous afternoon so far for {drv} in P{pos} — job ticking along.",
        "{drv} keeping their nose clean in P{pos}, nothing flashy.",
        "Workmanlike from {drv} in P{pos} — getting the most out of the package.",
        "{drv} consolidating in P{pos}, biding their time in the midfield.",
        "A measured race from {drv} in P{pos} — points the priority.",
        "{drv} in a holding pattern in P{pos}, waiting for an opportunity.",
        "P{pos} for {drv} — consistent if unspectacular, doing the job.",
        "{drv} running a clean, sensible race in P{pos} — tyre life preserved.",
        "Nothing to write home about from {drv} in P{pos}, but no disasters either.",
        "{drv} managing their race intelligently in P{pos} — every point counts.",
        "The points are there for {drv} in P{pos}, and right now that's enough.",
        "{drv} with a quiet P{pos} race — head down, banking the laps.",
        "Steady Eddie from {drv} — P{pos}, untroubled, and conserving for later.",
        "A professional job from {drv} in P{pos} — not glamorous, but effective.",
        "{drv} running in P{pos}, looking comfortable, not pushing beyond the limit.",
        "Controlled from {drv} in P{pos} — pace in hand, waiting for the late stages.",
        "{drv} getting the job done in P{pos} — not the headline, but on the board.",
        "Mid-race, mid-pack — {drv} in P{pos}, tucked in and biding time.",
        "A quiet race so far for {drv} — P{pos}, neat and tidy.",
        "No drama, no mistakes, no fuss — {drv} ticking along in P{pos}.",
        "Invisible in the best possible way — {drv} getting the most from P{pos}.",
        "{drv} in P{pos} — the kind of drive that gets forgotten but deserves credit.",
        "{drv} at P{pos} — not the star, but not the story either. Solid.",
        "In the thick of the midfield, {drv} is handling P{pos} with quiet professionalism.",
    ],
    "midpack_recovery": [
        "{drv} still fighting back — P{pos} now after the earlier drama, and moving forward.",
        "Remarkable resilience from {drv} — already up to P{pos} after what happened earlier.",
        "{drv} not giving up on this race — P{pos} now, grinding through the field.",
        "The comeback continues for {drv} — P{pos}, and every place from here is a bonus.",
        "{drv} showing real grit — up to P{pos} after the earlier setback, still hunting.",
    ],
    "midpack_spun": [
        "{drv} doing well to be at P{pos} after that spin — building it back lap by lap.",
        "P{pos} for {drv} — remarkable they're even this high after the earlier incident.",
        "{drv} making the most of a difficult afternoon — P{pos} a decent salvage job.",
        "Quietly rebuilding after the spin — {drv} now at P{pos}, still in the hunt.",
        "Character from {drv} — shook off the spin and is back to solid work at P{pos}.",
    ],
    "criticism": [
        "{drv} is having a scrappy one — untidy and bleeding time.",
        "That's messy from {drv}, struggling for any rhythm at all.",
        "{drv} looking ragged, the car a real handful at the moment.",
        "Mistakes creeping in for {drv} — it's just not clicking today.",
        "{drv} all over the place through there, losing chunks of time.",
        "A scruffy one from {drv}, well off the pace in the middle sector.",
        "{drv} fighting the car at every corner — that's hard work to watch.",
        "Another lock-up from {drv}, flat-spotting those tyres badly.",
        "{drv} running wide again — they just can't string a lap together.",
        "It's unravelling for {drv}, one error after another out there.",
        "{drv} is a passenger at the moment, the car completely out of shape.",
        "Way too aggressive from {drv}, and it's costing them dearly.",
        "{drv} bleeding time in every sector — the rhythm has deserted them.",
        "That's twitchy from {drv}, fighting the rear at every turn-in.",
        "{drv} braking far too deep and paying for it on the exits.",
        "The body language of that car says it all — {drv} really struggling.",
        "{drv} missing apexes left and right — this is a difficult watch.",
        "Tyres look shot for {drv}, sliding around like it's on ice.",
        "{drv} is overdriving badly, and the lap times are tumbling.",
        "Another scruffy lap from {drv} — confidence visibly drained.",
        "{drv} just can't get the car to do what they want today.",
        "Wild moment there for {drv} — hanging on rather than racing.",
        "The wheels are coming off {drv}'s race, figuratively speaking.",
        "{drv} losing the back end on every exit — no traction at all.",
        "It's a real handful for {drv}, and the stopwatch is unforgiving.",
        "{drv} flat-spotting tyres, running wide — it's all going wrong.",
        "Error-strewn stuff from {drv} — they'll want to forget this stint.",
        "The pace just isn't there for {drv} today — nothing in the toolbox.",
        "{drv} can't buy a clean lap — frustrated, ragged, off the pace.",
        "A difficult afternoon for {drv} — every mistake costing dearly.",
        "Nowhere near the pace — {drv} is losing ground with every sector.",
        "{drv} fighting everything — the car, the tyres, the circuit.",
        "Not the weekend {drv} was hoping for — sliding well off the pace.",
        "Understeer on entry, oversteer on exit — {drv} can't find the balance.",
        "{drv} is giving up too much time in the braking zones — costly.",
        "The car is a barge for {drv} today — they can't place it where they want.",
        "A race to forget is developing for {drv} — error after error after error.",
        "Confidence looks low for {drv} — not committing to the corners at all.",
        "{drv} needs to take a breath and reset — the driving is frantic and it's showing.",
        "The rear steps out AGAIN for {drv} — the set-up is not working today.",
        "{drv} losing half a second every lap in the medium-speed stuff — painful.",
        "You can see the struggle in every corner — {drv} just can't get a clean lap.",
        "A frustrating, scrappy, difficult afternoon for {drv} — nothing going right.",
        "{drv} is costing themselves dearly — talent's there, the execution is nowhere.",
        "The tyres are going away badly for {drv} — far too aggressive early on.",
        "One look at the telemetry and you'd see the problem — {drv} all over the throttle.",
        "Erratic inputs from {drv} — the car can't decide what it wants to do.",
        "Lock-ups, runoffs, missed apexes — {drv} is having a nightmare of a stint.",
        "{drv} in no-man's-land — too slow to challenge, too fast to manage the tyres.",
    ],
    "criticism_spun": [
        "{drv} yet to recover their composure after the spin — still losing time.",
        "The spin seems to have knocked the confidence from {drv} — tentative now.",
        "{drv} still feeling the effects of that earlier incident — pace remains elusive.",
        "A race defined by that spin for {drv} — struggling to find their feet since.",
        "The mistakes keep coming for {drv} — that spin really unsettled them.",
    ],
    "pregrid": [
        "Hello and welcome to RacerTV, live at {trk}! I'm {comm_full}, alongside {pundit_full} — let's go racing.",
        "You're watching RacerTV, live from {trk}. I'm {comm_full} with {pundit_full} — here we go.",
        "This is RacerTV at {trk}! {comm_full} and {pundit_full} in the booth. Lights are coming.",
        "Welcome to RacerTV! {comm_full} here with {pundit_full}, live at {trk}.",
        "Race day on RacerTV, live at {trk}! {comm_full} and {pundit_full} with you all the way.",
        "Welcome along to RacerTV at {trk}. I'm {comm_full}, joined by {pundit_full} — let's race.",
    ],
    "quali_start": [
        "Qualifying is underway here at {trk} — the hunt for pole begins!",
        "The session gets going at {trk}, everyone chasing that pole time.",
        "Out they go at {trk} — time to put a marker down in qualifying.",
        "Qualifying begins at {trk}. Who's got the lap to grab pole?",
    ],
    "practice_start": [
        "Practice is underway at {trk} — the teams getting to work.",
        "The session begins at {trk}, plenty of data to gather here.",
        "Out they come for practice at {trk}, dialing the cars in.",
    ],
    "quali_fastlap": [
        "{drv} goes quickest — a {gap} to top the timesheets!",
        "{drv} lights up the screens, fastest of all with a {gap}!",
        "That's the benchmark — {drv} on top, a {gap}!",
        "Purple sectors for {drv} — quickest in the session, {gap}!",
        "{drv} jumps to the top of the order with a {gap}!",
        "A flier from {drv}! {gap}, and that's good enough for top spot!",
    ],
    "quali_pole": [
        "{drv} takes provisional pole position!",
        "New man on top — {drv} bumps to P1 on the grid!",
        "{drv} goes fastest of all — provisional pole!",
        "Top of the timesheets now, and it's {drv}!",
        "{drv} demotes the field — that's provisional pole!",
        "Pole, for the moment, belongs to {drv}!",
    ],
    "quali_improve": [
        "{drv} improves — up to provisional P{pos}.",
        "A better lap from {drv}, climbing to P{pos} on the grid.",
        "{drv} finds time, into P{pos} provisionally.",
        "That's quicker from {drv} — up to P{pos}.",
        "{drv} moves up the order to P{pos}.",
        "Improvement for {drv}, now P{pos} on the timesheets.",
    ],
    # a driver banks/improves a lap — reported with their actual TIME + place,
    # so the booth has plenty of accurate, varied things to say in quali/practice
    "lap_report": [
        "{drv} fires in a {time} — that's good enough for P{pos}.",
        "A {time} for {drv}, up to P{pos} on the timesheets.",
        "{drv} improves to a {time}, into P{pos}.",
        "That's a {time} from {drv} — provisional P{pos}.",
        "{drv} finds time, a {time}, P{pos} now.",
        "Better from {drv}: a {time}, and that's P{pos}.",
        "{drv} dips to a {time}, climbing to P{pos}.",
        "Quicker again from {drv} — {time}, good for P{pos}.",
        "{drv} puts in a {time}, slotting into P{pos}.",
        "A tidy {time} from {drv} — up to P{pos}.",
        "{drv} banks a {time}, P{pos} as it stands.",
        "Strong lap from {drv}, a {time} — that's P{pos}.",
        "{drv} lights up the timing screens — a {time} for P{pos}.",
        "There's a marker from {drv}: {time}, good enough for P{pos}.",
        "{drv} on a flier — {time}, and that's P{pos} provisionally.",
        "A {time} for {drv}, climbing the order into P{pos}.",
        "{drv} delivers when it counts — {time}, P{pos}.",
        "Up goes {drv} — a {time} lifts them to P{pos}.",
        "{drv} finds the lap — {time}, slotting into P{pos}.",
        "Tidy from {drv}, a {time}, and that's P{pos} on the sheets.",
    ],
    "lap_report_slow": [
        "{drv} struggling for pace — well off the leaders down in P{pos}.",
        "Not coming together for {drv}, languishing in P{pos}.",
        "{drv} can't find a clean lap, stuck in P{pos} for now.",
        "A scrappy run from {drv} — only P{pos} to show for it so far.",
        "{drv} with work to do, adrift in P{pos} at the moment.",
    ],
    "quali_standings": [
        "Provisional grid: {p1} on pole from {p2} and {p3}.",
        "As it stands on the grid — {p1}, {p2}, then {p3}.",
        "{p1} heads the timesheets from {p2} and {p3}.",
        "Top three provisionally: {p1}, {p2} and {p3}.",
        "{p1} quickest so far, {p2} and {p3} chasing that pole time.",
        "The order at the top: {p1}, {p2}, {p3} — for now.",
    ],
    "quali_final": [
        "Into the closing stages of qualifying — last chance for a flyer!",
        "Final laps of the session now — it's all on the line!",
        "The clock's ticking down — who can find one last lap?",
        "Last runs going in, and this grid is taking shape!",
    ],
    # a flying lap DELETED for track limits
    "quali_deleted": [
        "{drv} has that lap deleted — exceeded track limits.",
        "Lap gone for {drv} — over the limits, that one won't count.",
        "{drv} loses the lap, all four wheels beyond the white line.",
        "Track limits catch out {drv} — that time is deleted.",
        "No good for {drv} — that lap's chalked off for track limits.",
    ],
    # SESSION STATE — how many have set a time, who's still in the pits
    "quali_count": [
        "{set} of the {total} cars have set a time so far.",
        "{set} of {total} drivers with a lap on the board now.",
        "So far {set} of {total} have banked a time — plenty still to come.",
        "{set} times set out of {total}; the rest still to show their hand.",
    ],
    "quali_onlyone": [
        "Only {drv} has set a time so far — everyone else still to run.",
        "Just the one lap on the board, and it belongs to {drv}.",
        "{drv} the only driver to have set a time so far.",
    ],
    # NOBODY has set a lap yet — the booth must NOT pretend the timing-tower
    # order is a grid; it's just who's registered. Stay neutral.
    "quali_nobody": [
        "No times on the board just yet — everyone still on their out-laps.",
        "Nobody's set a representative lap so far; the grid is still wide open.",
        "Clean sheet up on the timing screens — the first flier could come any moment.",
        "Still waiting for the first proper lap to go in here at {trk}.",
        "No benchmark set yet — the order means nothing until someone banks a time.",
    ],
    # SOLO session — just the player (and maybe a ghost) on track. Common in
    # RaceRoom practice and registered qualifying. {drv} = the player.
    "quali_solo": [
        "Just {drv} out on track today, getting some good laps in.",
        "A private session this — only {drv} circulating at {trk}.",
        "{drv} has the place to themselves, working through the running.",
        "No one else out here — {drv} alone, chasing a clean lap at {trk}.",
        "It's a solo run for {drv}, with all the clear track they could want.",
        "Quiet out there — {drv} the only car turning laps at {trk}.",
        "Nothing but clear air for {drv} — no traffic to worry about today.",
        "{drv} out there on their own, free to find a rhythm at {trk}.",
        "A peaceful session for {drv}, just car, track and the stopwatch.",
        "{drv} has the whole circuit as a private playground this afternoon.",
        "No rivals to measure against — just {drv} against the clock and {trk}.",
        "{drv} putting the laps in solo, no distractions, pure feel.",
        "The track belongs to {drv} today — every line, every apex, theirs to explore.",
        "Lonely but useful work for {drv} out there at {trk}.",
    ],
    # What a driver is trying to ACHIEVE in a practice/quali session — gives the
    # booth something substantial to say beyond 'they're out there'. {drv}=player.
    "quali_goals": [
        "{drv} will be working on the setup here — chasing that perfect balance for the race.",
        "This is all about banking laps for {drv} — learning the circuit, building confidence.",
        "Tyre management and braking points are the homework for {drv} today.",
        "{drv} hunting those last couple of tenths before it really counts.",
        "A clean, representative lap is what {drv} wants — to know exactly where they stand.",
        "Consistency first, outright pace second — that's the order of business for {drv}.",
        "{drv} fine-tuning the car, trying to unlock a bit more rotation through the slow stuff.",
        "The goal for {drv}: understand the tyres, nail the braking zones, build the speed.",
        "{drv} experimenting with lines and references, stitching the lap together.",
        "Long-run pace is what {drv} is studying here — how the tyres hold up over a stint.",
        "{drv} will want to leave this session knowing the car is race-ready.",
        "Bit of fuel and tyre work for {drv} — the unglamorous stuff that wins races.",
        "{drv} building up corner by corner, learning where the real limit lives.",
        "It's about confidence for {drv} — trusting the car so they can attack when it matters.",
    ],
    # the booth cracks a (light, racing-flavoured) joke now and then — sparingly,
    # to keep a quiet session warm. Persona-agnostic one-liners.
    "booth_joke": [
        "I'd tell you a joke about understeer, but you'd all see it coming a mile off.",
        "They say practice makes perfect — clearly nobody told my golf swing.",
        "It's so quiet out here you could hear a tyre temperature drop.",
        "An empty track and all the time in the world — living the dream, this.",
        "If concentration burned calories, these drivers would be racing snakes.",
        "I haven't seen lapping this lonely since I tried to organise a karting reunion.",
        "You know what they say — qualifying is just practice with anxiety.",
        "My doctor told me to avoid stress, so naturally I took up motor racing commentary.",
        "Plenty of clear track out there — not unlike my social calendar.",
        "Brakes warm, tyres warm, my coffee stone cold. The sacrifices we make.",
        "Slow in, fast out — the only advice that works for corners AND buffet queues.",
        "A flying lap, they call it. I've seen the catering, nobody's flying anywhere.",
    ],
    # OPEN / no-clock qualifying or practice (registered session, you + ghost,
    # no time limit) — there's no rush, so it's about banking the mileage.
    # {drv} = the player, {laps} = laps completed.
    "quali_open_laps": [
        "{drv} has completed {laps} laps now — really piling on the mileage.",
        "No clock to worry about here, and {drv} is up to {laps} laps. Plenty of practice going in.",
        "{laps} laps done for {drv} — making the most of an open session.",
        "{drv} keeps circulating, {laps} laps in the bag and counting. No pressure, just reps.",
        "That's {laps} laps for {drv} — banking experience with no time limit hanging over them.",
        "All the time in the world here — {drv} on {laps} laps, learning every inch of {trk}.",
    ],
    "quali_pits": [
        "Most of the field still in the pits, waiting for the right moment.",
        "A quiet track — plenty still in the garage, biding their time.",
        "Lots of cars in the pit lane, timing their run to the track evolution.",
        "The pit lane's busy — many holding off for clear air.",
    ],
    "practice_note": [
        "Useful running for {drv}, working through the program.",
        "{drv} out on track, banking laps and gathering data.",
        "Plenty of work for {drv} in this session, dialing the car in.",
        "{drv} putting the laps in here — building toward qualifying.",
        "Quietly productive from {drv}, learning the circuit.",
        "{drv} on a longer run, watching how the tyres hold up.",
        "Looks like a setup change for {drv} — back out to evaluate it.",
        "{drv} experimenting with lines through the middle sector.",
        "A short run for {drv}, then back to the garage for a look at the data.",
        "{drv} steadily building speed, no need to overdrive it here.",
        "Fuel and tyre work for {drv} — the unglamorous but vital stuff.",
        "{drv} chipping away, finding the limit corner by corner.",
    ],
    # neutral 'colour' valid in PRACTICE or QUALI (no race wording) — the
    # bread-and-butter chatter so the booth isn't just reciting track facts.
    "session_colour": [
        "The track's still rubbering in — grip improving every lap out there.",
        "Conditions look good here at {trk}, plenty of laps being banked.",
        "Interesting to see who's running and who's still in the garage.",
        "The circuit will only get quicker as more rubber goes down.",
        "Teams balancing tyre life against outright pace on these runs.",
        "A busy session, cars filtering in and out of the pit lane.",
        "Track temperature is a big factor for the tyres around here.",
        "Everyone hunting for that bit of clear space to show their hand.",
        "You can see the lines starting to form as the surface comes to them.",
        "Some on low fuel for a flyer, others clearly on heavier runs.",
        "It's a chess match out there — timing your lap to the track evolution.",
        "Plenty still being learned about the car and the circuit here.",
        "The quick guys are making this place look easy — it isn't.",
        "A lot of information being gathered for the engineers to chew on.",
        "Tyre warm-up is key around {trk} — get it wrong and the lap's gone.",
        "No prizes handed out yet, but reputations are quietly being built.",
    ],
    "track_generic": [
        "We're racing at the magnificent {trk} today.",
        "{trk} — a real test of car and driver, this one.",
        "A proper drivers' circuit, this — {trk}.",
        "Plenty of history around {trk}.",
        "{trk} rarely fails to deliver a spectacle.",
        "A circuit that punishes the slightest error, {trk}.",
        "The flow of {trk} really rewards a brave driver.",
        "{trk} — where reputations are made and lost.",
        "Few places test commitment like {trk} does.",
        "There's a unique rhythm to {trk}, and the best find it quickly.",
        "{trk} demands respect, and it's getting plenty today.",
        "A grand old venue, {trk} — racing the way it should be.",
        "Every corner at {trk} tells a story.",
        "The challenge of {trk} brings the very best out of these drivers.",
    ],
}

# track trivia & history, matched by a substring of the circuit name. Mixes
# geography, character and FAMOUS RACES so the booth tells the venue's story.
# short, broadcast-friendly track names — RaceRoom's track_name is often verbose
# ("Circuit de Spa-Francorchamps Grand Prix"), and saying the full thing every
# time is clunky. Matched by substring; first hit wins (order matters where one
# venue contains another, e.g. Nordschleife before Nürburgring).
SHORT_TRACK = {
    "nordschleife": "the Nordschleife",
    "nurburg": "the Nürburgring",
    "laguna": "Laguna Seca",
    "bathurst": "Bathurst",
    "panorama": "Bathurst",
    "spa": "Spa",
    "monza": "Monza",
    "suzuka": "Suzuka",
    "imola": "Imola",
    "silverstone": "Silverstone",
    "zandvoort": "Zandvoort",
    "brands hatch": "Brands Hatch",
    "hockenheim": "Hockenheim",
    "red bull ring": "the Red Bull Ring",
    "spielberg": "the Red Bull Ring",
    "interlagos": "Interlagos",
    "watkins": "Watkins Glen",
    "road america": "Road America",
    "indianapolis": "Indianapolis",
    "daytona": "Daytona",
    "le mans": "Le Mans",
    "hungaroring": "the Hungaroring",
    "zolder": "Zolder",
    "zhuhai": "Zhuhai",
    "sonoma": "Sonoma",
    "sebring": "Sebring",
    "portimao": "Portimão",
    "portimão": "Portimão",
    "barcelona": "Barcelona",
    "catalunya": "Barcelona",
    "paul ricard": "Paul Ricard",
    "norisring": "the Norisring",
    "salzburgring": "the Salzburgring",
    "mid-ohio": "Mid-Ohio",
    "macau": "Macau",
    "dubai": "Dubai",
    "moscow": "Moscow Raceway",
    "anderstorp": "Anderstorp",
    "oschersleben": "Oschersleben",
    "lausitz": "the Lausitzring",
    "slovakia": "the Slovakia Ring",
    "ningbo": "Ningbo",
    "chang": "Chang",
    "raceroom": "RaceRoom Raceway",
}

# REAL track tips the RACE ENGINEER relays to help you find pace (second person,
# actionable). Keyed by track substring (same keys as SHORT_TRACK). Used across
# all sessions, especially practice/quali. Kept to genuine, well-known advice.
TRACK_TIPS = {
    "spa": [
        "Sector one's all about the launch out of La Source — short-shift, get traction, then commit to Eau Rouge.",
        "Eau Rouge into Raidillon: lift a fraction on entry, but stay flat over the crest once you trust it. Lifting there costs you the whole Kemmel straight.",
        "Down the Kemmel, tuck in for the tow and brake deep into Les Combes — it's the best overtaking spot on the lap.",
        "Sector two is where the lap's won — Pouhon is a single, smooth double-apex arc. No mid-corner corrections, just commit.",
        "Be patient into the Bus Stop chicane — get it slowed, square the exit, and you get a clean run to the line.",
        "Through Stavelot, get on the power early; the exit feeds the long run down to the Bus Stop.",
        "Blanchimont is flat if the car's stable — but only commit there once your rear's planted, it bites hard.",
        "Rivage hairpin: brake in a straight line, hug the inside, and don't run wide — the exit kerb is your friend.",
        "Don't chase Eau Rouge if the lap's scrappy — the real time at Spa is consistency through the middle sector.",
    ],
    "monza": [
        "Sector one is the first chicane — brake as late as you dare, but get it slowed. A tidy exit beats a heroic entry every time.",
        "Use all the kerb through the two Lesmos to open the corner and protect your exit onto the straight.",
        "Ascari is the key — a left-right-left flick. Commit to the first part and the rest links up; mess up the entry and you lose the whole sequence.",
        "Parabolica: get the car rotated early on entry, then feed the throttle all the way for the long blast to the line.",
        "Run minimum wing here — the car will feel nervous under braking, so brake earlier and trust the slipstream for passes.",
        "The Variante della Roggia is your second-best passing spot — late on the brakes down the inside.",
        "Don't overdrive the chicanes chasing kerb — clip them clean, because a hop unsettles the car for the exit.",
        "Slipstream is everything at Monza — sit in the tow, then dive late into the first chicane or Roggia.",
    ],
    "silverstone": [
        "Sector one: Abbey is near-flat, then commit to Farm — carry the speed, the car can take more than you think.",
        "Maggotts and Becketts is the signature complex — minimal steering input, carry the speed, and never lift mid-sequence.",
        "Copse rewards confidence — it's a small lift, not a brake, once you trust the front end.",
        "Brake in a straight line for Stowe, then one smooth input. Don't trail the brake too deep or you'll wash wide.",
        "Get a clean exit out of Chapel — that sets up your entire run down the Hangar Straight.",
        "Vale into Club: heavy braking, get it stopped, then a patient exit to fire onto the start-finish straight.",
        "The Loop hairpin is a traction zone — square it off, short-shift, protect the run to Aintree.",
        "Brooklands and Luffield are slow and frustrating — patience and a tidy exit matter far more than entry speed.",
    ],
    "suzuka": [
        "Sector one is the Esses — pure rhythm. Get the first flick right and the rest flow; fight the car in one and you lose them all.",
        "Turn one and two: brake in a straight line, then a single arc down to the Esses entry.",
        "Degner one and two punish greed — respect them, get the car settled, the time is elsewhere.",
        "The hairpin is all about exit — short-shift, get traction, fire out toward Spoon.",
        "Spoon Curve is a double-apex — be patient on entry, get to the second apex, then full commit for the back straight and 130R.",
        "130R: lift early rather than braking mid-corner — carry the minimum speed cleanly and it's basically flat.",
        "Be patient into the final Casio chicane — a clean exit is both your lap time and your overtake into turn one.",
        "It's a figure-eight that flows — smoothness beats aggression everywhere except the hairpin and chicane.",
    ],
    "laguna": [
        "The Corkscrew is the whole track — aim for the tree, brake before the crest, then let the car fall through the left-right. Don't force the wheel.",
        "Turn two is heavy braking after the run up the hill — square it off and fire out for the climb.",
        "Turn five up the hill: be patient, the exit is blind over the crest — get it right before you commit.",
        "Rainey Curve after the Corkscrew is downhill and decreasing — be gentle, it's easy to run wide there.",
        "It's a momentum circuit — protect every exit, especially the last corner onto the front straight.",
        "Turn eleven, the final hairpin: get it stopped, then traction is king onto the pit straight.",
        "Don't overdrive the Corkscrew entry — the time is carrying speed THROUGH it, not braking late into it.",
    ],
    "imola": [
        "Sector one: Tamburello and Villeneuve are flowing chicanes now — flow through, don't stab the brakes.",
        "Attack the kerbs through the Variante Alta chicane, but stay clean on the exit — a hop there costs you the climb.",
        "Acque Minerali: patience on entry, the downhill exit comes at you fast. Don't run wide on the way out.",
        "Piratella is blind over the crest — commit early and trust the line, it drops away after the apex.",
        "Rivazza is two lefts downhill — get the first one slowed, then a clean exit fires you onto the straight.",
        "Track position is gold here — it's hard to pass, so prioritise a clean lap over a heroic one.",
        "The Variante Bassa run to the line — get traction, no wheelspin, every tenth counts on this short lap.",
    ],
    "bathurst": [
        "Sector one is the run up Mountain Straight — get a clean exit from Hell Corner and ride it out.",
        "Across the top of the Mountain, commit and trust your markers — there's no room, but lifting up there costs enormous time.",
        "The Cutting is steep uphill and tight — get it slowed, then drive out, the climb saps your speed.",
        "Skyline into the Esses: it drops away dramatically — be smooth, let the car settle, then thread the dipper.",
        "Forrest's Elbow sets up the whole run down Conrod — a clean, committed exit or you bleed speed for a kilometre.",
        "Conrod Straight is flat-out — then The Chase is heavy braking after huge speed. Brake earlier than feels right; it builds confidence.",
        "Across the top there's nowhere to recover a mistake — smooth and precise beats brave and ragged every single lap.",
    ],
    "nordschleife": [
        "It's all about memory — build up gradually, learn what's over each crest before you commit. Knowledge is lap time here.",
        "Be smooth and patient — the Green Hell punishes greed far more than caution.",
        "Through the Caracciola Karussell, drop into the banking and let the camber do the work — don't fight it.",
        "Fuchsröhre is fast and plunging — commit on the way down, but the compression at the bottom loads the car hard.",
        "Schwedenkreuz is flat-out bravery — only commit once you trust the car over the crests.",
        "Pflanzgarten: respect the jumps — get the car settled before each, landing crooked ends your lap.",
        "Brünnchen and the corners before it are slow and technical — bank the traction, the long sections reward patience.",
        "On a hot lap, leave a margin — there are no run-offs out here, a small mistake is a big one.",
    ],
    "interlagos": [
        "Sector one: the Senna S — a smooth, linked left-right downhill. Don't brake too deep into the first part.",
        "Carry speed through Curva do Sol onto the back straight — that's a big chunk of your lap time.",
        "Descida do Lago: brake downhill, get it stopped, clean exit — it's a passing spot too, so defend the inside.",
        "Ferradura is a long right that tightens — be patient, get to the apex late, then power out.",
        "Juncão is THE corner — get a clean, traction-rich exit because it feeds the long uphill climb to the line.",
        "Protect your exit from the final corner — the climb to the line magnifies any wheelspin into lost tenths.",
        "It runs anti-clockwise and it's bumpy — let the car move around, don't fight every wiggle.",
    ],
    "zandvoort": [
        "Trust the banking — through Hugenholtz and the final Arie Luyendyk turn, commit and let the camber carry the speed.",
        "Tarzan, turn one, is the big passing spot — brake late down the inside, the banking helps you hold it.",
        "A clean exit off the final banked turn is everything — it feeds the main straight and your overtake into Tarzan.",
        "The middle sector is tight and undulating — be precise, the banked corners punish a messy line.",
        "Don't lift mid-corner on the banking — a smooth, single commitment is faster and safer than second-guessing.",
        "Turn three, the hairpin, is a traction zone — square it off and fire out toward the back of the lap.",
    ],
    "red bull ring": [
        "It's a traction track — the lap is three big braking zones, so it's all about clean exits, not entry heroics.",
        "Turn one: don't overslow it, trail the brake and let the car drift out to the exit kerb.",
        "Turn three is the prime overtake — uphill braking, dive down the inside and get it stopped.",
        "Turn four (the Rauch) — get a strong exit, it feeds the run up to the top of the hill.",
        "The Rindt and the final corner: get traction, no wheelspin, because every exit here leads to a straight.",
        "Short lap, so every tenth in the corners is amplified — be precise and clinical, not aggressive.",
    ],
    "le mans": [
        "Top speed matters, but the Porsche Curves are where you find real time — flow through, don't stab the brakes.",
        "Brake in a straight line for the two Mulsanne chicanes, then fire out — those exits win you the long straights.",
        "Indianapolis and Arnage: heavy braking then a tight, slow exit — patience and traction, not bravery.",
        "Tertre Rouge sets up the whole Mulsanne — a clean, committed exit is worth several km/h all the way down.",
        "The Ford chicanes before the line — get them slowed, kerb them clean, no hop, then traction to the flag.",
        "It's a long race — be smooth, save the car and the tyres, consistency beats a hero lap out here.",
    ],
    "nurburg": [
        "On the GP circuit, focus on the technical infield — traction and patience, not bravery, find the time.",
        "Turn one (the Castrol-S) is a key passing spot — brake late, get it stopped, clean exit.",
        "The Dunlop hairpin and the Veedol chicane: get them slowed, square the exits, protect the straights.",
        "Get the car settled before you commit through the fast NGK and Schumacher esses — clean exits matter most.",
        "The Mercedes Arena is slow and fiddly — smooth, linked inputs, don't fight the car through there.",
    ],
    "hockenheim": [
        "The stadium section is where the lap comes alive — tight, rhythmic, and all about clean linked exits.",
        "The hairpin (turn six) is the big overtake — brake deep down the inside, but get it stopped for the exit.",
        "Turn one: get a good exit, it feeds the long run down to the first proper braking zone.",
        "Be patient through the Parabolika and the fast stuff — let the car settle, then attack the stadium.",
        "The Sachskurve into the stadium — traction is everything, fire out clean toward the grandstands.",
    ],
    "brands hatch": [
        "Paddock Hill Bend is the iconic one — it drops away sharply after the apex, so brake early, get the car turned, and let it fall down the hill.",
        "Druids hairpin: brake late uphill, but get it slowed — the exit down to Graham Hill bend matters.",
        "Surtees and the run onto the back straight — a clean exit is worth a lot down to Hawthorn.",
        "Clearways/Clark Curve is long and onto the pit straight — be patient, get traction, carry the speed home.",
        "It's short and flowing — rhythm and commitment over Paddock and through the dips win the lap.",
    ],
    "hungaroring": [
        "It's a tight, twisty 'street circuit without walls' — rhythm and traction matter more than top speed.",
        "Turn one is the main passing spot — brake late down the inside, but get it stopped for the downhill exit.",
        "Turns two and three flow together downhill — be smooth, link them, don't brake too deep into two.",
        "The final sector is a series of medium corners — clean exits stack up, prioritise traction everywhere.",
        "Track position is king — it's notoriously hard to pass, so a clean qualifying lap is worth gold.",
    ],
    "zolder": [
        "It's a stop-start rhythm track — the chicanes demand a clean, kerb-clipping line without unsettling the car.",
        "The first chicane is the prime overtake — brake late down the inside and square the exit.",
        "Get traction out of the slow corners — Zolder rewards a planted rear and patient throttle.",
        "The fast Terlamenbocht needs commitment — trust the car and carry the speed onto the straight.",
    ],
    "sonoma": [
        "It's hilly and blind — many corners crest and drop, so learn the exits before you commit on entry.",
        "Turn seven, the hairpin, is a key passing spot — brake late downhill, get it stopped, fire out.",
        "The Carousel (turn six) is long and off-camber — be patient, a single smooth arc.",
        "Turn two over the crest is blind — commit to the line you've learned, don't lift mid-corner.",
        "Protect your exits — traction off the slow stuff onto the straights is where the lap is.",
    ],
    "sebring": [
        "The track surface is famously bumpy — let the car move around, don't fight every bump, stay loose on the wheel.",
        "Turn one and seventeen bookend the lap — clean exits onto the long straights are vital.",
        "The Hairpin (turn seven) is the big stop — brake deep but get it slowed for traction out.",
        "Sunset Bend and the fast stuff: commit, but respect the bumps loading the car mid-corner.",
        "It's tough on the car over a stint — smoothness saves the tyres and your lap consistency.",
    ],
    "portim": [   # matches both "Portimão" and the ASCII "Portimao"
        "It's a rollercoaster — blind crests and big elevation. Learn what's over each rise before you commit.",
        "Turn one drops away after the apex — brake early, get it turned, let the car fall down the hill.",
        "The fast downhill stuff needs trust — commit over the crests, the grip is there once you know the line.",
        "The final corner onto the straight is crucial — a clean, traction-rich exit defines your lap time.",
        "Be smooth through the undulations — fighting the car over the crests just scrubs speed.",
    ],
    "barcelona": [
        "Sector three (the final chicane and slow stuff) is where laps are lost — get traction, don't overdrive it.",
        "Turn one is the main overtake — brake late down the inside, but get it stopped for the long turn two.",
        "Turn three is a long right onto the back straight — patient entry, get to the apex, then full throttle.",
        "The fast turn nine (Campsa) is blind over a crest — commit early, trust the line.",
        "It's hard on the front tyres — manage them, because the long corners punish understeer late in a stint.",
    ],
    "paul ricard": [
        "The long Mistral straight (often split by a chicane) means top speed matters — but the technical end is where the lap is.",
        "Signes at the end of the Mistral is high-speed — lift only slightly if at all, but respect it.",
        "The double-apex Beausset needs a patient entry — get to the second apex, then power out.",
        "Use the run-off paint as a reference but stay within track limits — it's easy to lose a lap to the lines here.",
        "Get traction out of the slow chicane complex — clean exits define the lap.",
    ],
    "norisring": [
        "It's a short, slow street circuit — basically two straights and a hairpin, so it's all about braking and traction.",
        "The Grundigkehre hairpin is the big stop — brake deep, get it slowed, traction is everything on exit.",
        "Ride the kerbs through the chicane but don't unsettle the car — a hop kills your straight-line speed.",
        "Slipstream matters on the straights — sit in the tow and brake late into the hairpins.",
    ],
    "salzburgring": [
        "It's a fast, flowing track in a valley — high-speed commitment, not slow-corner traction, wins the lap.",
        "The Fahrerlagerkurve hairpin at the end is the only real stop — brake hard, get it slowed, fire back out.",
        "The fast Nockstein sweepers need trust — carry the speed, lift rather than brake where you can.",
        "It's narrow with little run-off — leave a margin on a hot lap, mistakes are costly here.",
    ],
    "mid-ohio": [
        "It's tight and technical with elevation — rhythm and clean exits matter more than outright bravery.",
        "The Keyhole (turn two) is a long, slow corner — be patient, get a tidy exit onto the back section.",
        "The Esses flow downhill — link them smoothly, don't brake too deep into the first one.",
        "Carousel and the Madness: commit and trust the line, the time is in carrying speed through the fast stuff.",
        "Protect your exit onto the front straight — traction there is a big part of the lap.",
    ],
    "macau": [
        "It's a tight street circuit with walls everywhere — there's zero margin, so build up gradually.",
        "The Lisboa hairpin after the long straight is THE overtaking spot — brake late, but get it stopped.",
        "The mountain section (Solitude to Moorish Hill) is barely a car-width wide — smooth and precise, never greedy.",
        "Get a clean exit onto the long Guia straight — it's where you'll set up every pass into Lisboa.",
        "Respect the walls — at Macau, finishing the lap clean is worth more than the last tenth.",
    ],
    "dubai": [
        "It's a flat, technical track — traction out of the slow corners is where the lap time lives.",
        "The big braking zones reward late, stable braking — get the car stopped and square the exit.",
        "Link the fast esses smoothly — don't fight the car, carry the speed through the flowing parts.",
        "Tyre management matters in the heat — be smooth, the surface is abrasive over a stint.",
    ],
    "road america": [
        "It's fast and flowing with long straights — top speed and clean exits onto them define the lap.",
        "The Carousel is long and onto a straight — be patient, get to the apex, then full commitment out.",
        "Canada Corner is a prime overtake — brake late down the inside, get it stopped, traction out.",
        "The Kink is high-speed — flat or near-flat once you trust the car, but it bites if the rear's loose.",
        "Protect exits onto the long straights — a tenth gained there multiplies down the back stretch.",
    ],
    "watkins": [
        "The Esses are the signature — flow through, minimal steering, carry the speed and never lift mid-sequence.",
        "Turn one (the ninety) is the main stop — brake late down the inside, square the exit.",
        "The Bus Stop chicane (the inner loop) — get it slowed, kerb it clean, no hop, then traction out.",
        "The Toe is fast onto the back straight — commit and protect that exit for top speed.",
        "It's quick and committed — smoothness through the Esses is worth more than late braking anywhere.",
    ],
    "indianapolis": [
        "On the road course, the infield is tight and technical — traction and patience win it, not the banking.",
        "Turn one off the straight is the big stop — brake late, get it slowed for the infield run.",
        "Link the infield esses smoothly — they're stop-start, so clean exits stack up.",
        "Protect the exit onto the long straight — that's where the lap time and the overtakes are.",
    ],
    "daytona": [
        "On the road course you blend banking and infield — carry the banked speed, but the infield is where laps are won.",
        "The Bus Stop chicane on the back straight — brake hard, kerb it clean, get traction out.",
        "The banking is near-flat — stay smooth and high, let the car run, don't scrub speed fighting it.",
        "The infield is tight and flat — traction out of the slow corners onto the banking is key.",
    ],
    "zhuhai": [
        "It's a technical track with one long straight — traction out of the final corner feeds your top speed.",
        "Turn one after the straight is the main overtake — brake late, but get it stopped for the long right.",
        "The hairpins reward patience — get them slowed, square the exits, don't overdrive entry.",
        "Link the fast esses smoothly and protect the exit onto the main straight.",
    ],
    "sachsenring": [
        "It's tight and undulating — the long Omega/Sachsenkurve complex is the signature, all about a flowing line.",
        "The downhill Sachsenkurve is blind and committed — trust the line, let the car fall through it.",
        "Get traction out of the slow corners — the lap rewards a planted rear and patient throttle.",
    ],
    "moscow": [
        "It's flat and technical — late braking into the slow corners and traction out is the recipe.",
        "Link the chicanes cleanly without unsettling the car — a hop over the kerbs costs you the exit.",
        "Protect your exits onto the straights — that's where this lap is won.",
    ],
    "anderstorp": [
        "It's flat with a famously long back straight — traction out of the final corner is huge for top speed.",
        "The fast sweepers reward commitment — carry the speed, lift rather than brake where you can.",
        "The slow corners are about traction — square them off, no wheelspin onto the straights.",
    ],
    "oschersleben": [
        "It's tight and technical — rhythm through the linked corners and clean exits define the lap.",
        "The hairpins reward patience — get them slowed, then traction out.",
        "Kerb the chicanes cleanly — don't unsettle the car, protect the exit speed.",
    ],
    "lausitz": [
        "On the road course it's flat and technical — late braking and traction out of the slow stuff wins it.",
        "Get a clean exit onto the straights — that's where the lap time lives.",
        "Be smooth through the linked corners, don't overdrive the entries.",
    ],
    "slovakia": [
        "It's flowing and technical — rhythm through the fast esses matters more than outright braking.",
        "Carry speed through the quick corners — commit and trust the line.",
        "Protect your exits onto the straights with clean traction.",
    ],
    "ningbo": [
        "It's a modern technical track — traction out of the slow corners onto the straights is the priority.",
        "The big braking zones reward late, stable braking — get it stopped and square the exit.",
        "Link the esses smoothly and don't overdrive the tight stuff.",
    ],
    "chang": [
        "It's flat with long straights — traction out of the slow corners feeds your top speed.",
        "The heavy braking zones at the end of the straights are prime overtakes — brake late, get it stopped.",
        "Tyre and brake management matter in the heat — be smooth over a stint.",
    ],
    "raceroom": [
        "It's a flowing, purpose-built lap — rhythm and clean exits matter more than late-braking heroics.",
        "Carry speed through the fast sweepers — commit and trust the car.",
        "Protect your exits onto the straights for top speed.",
    ],
}

TRACK_FACTS = {
    "laguna": [
        "This is Laguna Seca, home of the legendary Corkscrew — a blind, plunging "
        "drop that's one of the most famous corners in all of motorsport.",
        "The Corkscrew falls nearly six storeys in just a few hundred metres.",
        "Who could forget Alex Zanardi's pass around the outside of the Corkscrew "
        "here — one of the boldest overtakes ever seen.",
        "Rossi versus Stoner in 2008, side by side through the Corkscrew — that "
        "duel is the stuff of Laguna Seca legend.",
        "It's a short lap, but every corner here demands absolute precision.",
    ],
    "bathurst": [
        "Mount Panorama at Bathurst — over a hundred and seventy metres of "
        "elevation change across the mountain.",
        "Bathurst is part street circuit, part race track, and all intimidating.",
        "The Bathurst 1000 is one of the great endurance classics — they call it "
        "the race that stops a nation in Australia.",
        "Across the top of the mountain there's barely a car's width of room — get "
        "it wrong here and there's nowhere to go.",
        "Peter Brock made this mountain his own — the King of the Mountain himself.",
    ],
    "panorama": [
        "Mount Panorama — few circuits in the world are as daunting as this run "
        "across the mountain.",
        "The dash down Conrod Straight is one of the great flat-out blasts in "
        "motorsport.",
    ],
    "spa": [
        "Spa-Francorchamps, and that's the legendary Eau Rouge and Raidillon "
        "complex, taken almost flat out by the very brave.",
        "Spa is famous for its microclimate — bone dry at one end, pouring with "
        "rain at the other.",
        "Who could forget Schumacher carving through the field here in the wet — "
        "Spa has always rewarded the truly fearless.",
        "At over seven kilometres, this is the longest lap of the season — a "
        "proper old-school road course.",
        "Eau Rouge has tested the nerve of every great driver in history.",
    ],
    "monza": [
        "Monza, the Temple of Speed — the fastest circuit of them all.",
        "The old banking still stands here, a haunting monument to the track's "
        "incredible and sometimes tragic history.",
        "The Monza tifosi are the most passionate fans in the world — a sea of red "
        "every single year.",
        "Slipstreaming battles down these long straights have produced some of the "
        "closest finishes the sport has ever seen.",
        "Peter Gethin won here in 1971 by one hundredth of a second — the closest "
        "finish in Grand Prix history.",
    ],
    "nurburg": [
        "The mighty Nürburgring — steeped in more history than almost anywhere in "
        "the sport.",
        "This is where Niki Lauda had his fiery accident in 1976, and astonishingly "
        "was racing again just weeks later.",
    ],
    "nordschleife": [
        "The Nordschleife — the Green Hell, over twenty kilometres and a hundred "
        "and fifty corners.",
        "Jackie Stewart christened this place the Green Hell, and the name stuck.",
        "Stirling Moss and Jackie Stewart both produced wet-weather masterclasses "
        "around this terrifying place.",
    ],
    "suzuka": [
        "Suzuka, with its unique figure-of-eight layout — the only one of its kind "
        "on the calendar.",
        "The Esses here are a glorious rhythm section, a true test of precision.",
        "So many championships have been decided at Suzuka — the infamous "
        "Senna–Prost collisions among them.",
        "130R is one of the great high-speed corners left in the sport.",
    ],
    "imola": [
        "Imola, a classic old-school circuit that runs anti-clockwise and demands "
        "total respect.",
        "This place will forever be remembered for that tragic weekend in 1994 — "
        "the sport changed completely afterwards.",
    ],
    "silverstone": [
        "Silverstone, the home of British motor racing — it hosted the very first "
        "World Championship Grand Prix back in 1950.",
        "Maggotts and Becketts is one of the great high-speed sequences anywhere "
        "in the world.",
        "Nigel Mansell gave Nigel Mansell fans the famous Silverstone moment — "
        "the crowd invasion of 1992 will never be forgotten.",
        "An old airfield circuit, fast and flowing, where bravery is everything.",
    ],
    "zandvoort": [
        "Zandvoort, with its dramatic banked corners nestled in the sand dunes.",
        "The banking lets the drivers carry astonishing speed — a real throwback.",
    ],
    "brands hatch": [
        "Brands Hatch — a rollercoaster of elevation through the Grand Prix loop.",
        "Paddock Hill Bend, plunging away downhill, is one of Britain's great "
        "corners.",
    ],
    "hockenheim": [
        "Hockenheim, once a flat-out blast through the dark forest, now a stadium "
        "circuit.",
        "The old forest layout was blisteringly fast — a very different beast.",
    ],
    "red bull ring": [
        "The Red Bull Ring — short, sharp, and set against the beautiful Styrian "
        "mountains.",
        "Formerly the daunting old Österreichring, one of the fastest tracks the "
        "sport has ever known.",
    ],
    "spielberg": [
        "This Austrian circuit is one of the shortest laps of the year — blink and "
        "it's over.",
    ],
    "interlagos": [
        "Interlagos in São Paulo — a short anti-clockwise lap that always seems to "
        "deliver drama.",
        "This is Ayrton Senna's home circuit — his emotional 1991 win here, "
        "stuck in sixth gear, is the stuff of legend.",
        "So many title deciders have come down to the wire at Interlagos.",
    ],
    "watkins": [
        "Watkins Glen, a fast, flowing classic of American road racing.",
    ],
    "road america": [
        "Road America — four miles of fast, sweeping curves through the Wisconsin "
        "countryside, barely changed in decades.",
    ],
    "indianapolis": [
        "Indianapolis, the Brickyard, with well over a century of racing history.",
        "A yard of bricks still marks the start-finish line — a nod to its origins.",
    ],
    "daytona": [
        "Daytona, with its steep high banking — a true test of bravery and "
        "machinery.",
        "The Daytona 24 Hours is one of the cornerstones of endurance racing.",
    ],
    "le mans": [
        "Le Mans — the spiritual home of endurance racing, where the Mulsanne "
        "Straight goes on and on.",
        "The Ford versus Ferrari battles of the 1960s here are the stuff of "
        "Hollywood legend.",
        "Twenty-four hours of flat-out racing — it punishes the smallest mistake.",
    ],
    "hungaroring": [
        "The Hungaroring — tight, twisty and relentless. They call it Monaco "
        "without the walls.",
        "Hungary was the first Grand Prix held behind the Iron Curtain, back in "
        "1986 — a genuine moment in the sport's history.",
        "Overtaking is famously hard here, so qualifying and strategy carry "
        "enormous weight.",
        "Nigel Mansell's charge from twelfth in 1989 is one of the great drives "
        "this circuit has ever seen.",
        "It's hot, dusty and physical — a real test of concentration with barely "
        "a straight to catch your breath.",
    ],
    "zolder": [
        "Circuit Zolder, set in the Belgian sand — fast, flowing and unforgiving.",
        "This place will always be remembered as where the great Gilles "
        "Villeneuve lost his life in 1982.",
        "The chicanes are the key here — kerb them hard, but get greedy and "
        "they'll spit you off.",
        "A proper old-school European circuit that rewards bravery through the "
        "quick stuff.",
    ],
    "zhuhai": [
        "Zhuhai — China's first purpose-built circuit, and a real test of a "
        "complete lap.",
        "That long back straight makes the slipstream and the heavy braking "
        "zone the place to attack.",
        "Technical and flowing in the middle sector — rhythm is everything "
        "around here.",
    ],
    "sonoma": [
        "Sonoma Raceway, carved into the Californian wine-country hills — all "
        "elevation and commitment.",
        "Once known as Sears Point, it's hosted NASCAR and IndyCar's finest for "
        "decades.",
        "The downhill esses give you no margin — get it wrong and the gravel is "
        "waiting.",
        "Blind crests and off-camber corners make this one of America's great "
        "driver's tracks.",
    ],
    "sebring": [
        "Sebring — twelve hours of the most punishing endurance racing on "
        "earth, on an old Second World War airfield.",
        "That bumpy concrete shakes the cars to pieces — survive Sebring and "
        "you can survive anywhere.",
        "The 12 Hours is one of the crown jewels of sportscar racing, run here "
        "since 1952.",
        "It's brutally physical and brutally hard on the machinery — a true "
        "test of car and driver.",
    ],
    "portim": [
        "Portimão, the Algarve circuit — a rollercoaster of blind crests and "
        "plunging elevation changes.",
        "Modern but ferociously challenging, it rewards a driver brave enough "
        "to commit over those blind brows.",
        "You can't see the apex on half these corners — it takes real faith in "
        "the line.",
        "The undulations here are like nowhere else on the calendar — pure "
        "white-knuckle stuff.",
    ],
    "barcelona": [
        "Barcelona-Catalunya — every team in the world knows this place inside "
        "out from years of testing.",
        "The abrasive surface chews through tyres, so management is the name of "
        "the game here.",
        "The long run to turn one is the best overtaking chance, but track "
        "position is gold around the rest of the lap.",
        "That final sector has tortured drivers for years — it's where good "
        "laps go to die.",
    ],
    "paul ricard": [
        "Paul Ricard, with those distinctive blue and red run-off stripes — "
        "unmistakable from the air.",
        "The long Mistral straight is the signature, split by a chicane and "
        "perfect for a slipstream battle.",
        "A favourite test venue in the south of France — fast, hot and "
        "abrasive on the tyres.",
        "Those painted run-offs are deceptively brutal — stray onto them and "
        "you'll lose all your grip.",
    ],
    "norisring": [
        "The Norisring — a tight little street circuit around the old rally "
        "grounds in Nuremberg.",
        "It's a stop-and-go blast: huge braking zones, two hairpins, and the "
        "spiritual home of the DTM.",
        "Short, sharp and unforgiving — barely a corner where you can relax.",
        "The big grandstand hairpin is where the overtakes happen, and where "
        "the brakes take a beating.",
    ],
    "salzburgring": [
        "The Salzburgring — threaded through an Austrian valley, fast and "
        "narrow with the mountains right there.",
        "It's flat-out and flowing, with precious little run-off — a real "
        "old-school test of nerve.",
        "The tight hairpin at the end is the one big stop on an otherwise "
        "high-speed blast.",
    ],
    "macau": [
        "The Guia Circuit at Macau — one of the most dangerous and revered "
        "street tracks in the world.",
        "Lisboa corner is the great overtaking spot, but the mountain section "
        "is barely wider than the cars.",
        "Senna, Schumacher, Häkkinen — the Macau Grand Prix has launched the "
        "careers of so many greats.",
        "There's no margin for error here at all — the walls are right there, "
        "the whole way around.",
    ],
    "dubai": [
        "The Dubai Autodrome — a modern, flowing circuit best known for its "
        "gruelling 24-hour race.",
        "Floodlit night running gives this place a special atmosphere under "
        "the desert sky.",
        "Technical and rhythmic, it rewards a driver who can string the "
        "esses together cleanly.",
    ],
    "moscow": [
        "Moscow Raceway — a modern, flat and technical circuit on the outskirts "
        "of the Russian capital.",
        "It's all about late braking into the slow corners and nailing the "
        "traction back out.",
        "Linking the chicanes cleanly is where the lap time hides here.",
    ],
    "anderstorp": [
        "Anderstorp, the Scandinavian Raceway — a slice of 1970s Formula One "
        "history out in the Swedish countryside.",
        "That enormous back straight, built on an airfield, makes top speed and "
        "traction absolutely critical.",
        "Ronnie Peterson's home race — the flying Swede thrilled the locals "
        "here.",
        "Flat and fast, it's a unique throwback to a very different era of "
        "racing.",
    ],
    "oschersleben": [
        "Motorsport Arena Oschersleben — tight, technical and a long-time "
        "touring car favourite in Germany.",
        "Rhythm through the linked corners is everything; there's nowhere to "
        "make up a big chunk of time.",
        "The hairpins reward patience and a clean exit onto the short "
        "straights.",
    ],
    "lausitz": [
        "The Lausitzring — a German tri-oval with a twisting infield, unusual "
        "on the European calendar.",
        "This is where Alex Zanardi had his terrible CART crash in 2001 — and "
        "his recovery became one of sport's great stories of courage.",
        "Part banked oval, part technical infield — it asks two very different "
        "things of a driver.",
    ],
    "slovakia": [
        "The Slovakia Ring — long, modern and flowing, one of central Europe's "
        "hidden gems.",
        "It's all about carrying speed through the fast sweepers and trusting "
        "the line.",
        "A real momentum circuit — lift, don't brake, where you can.",
    ],
    "ningbo": [
        "Ningbo, on China's east coast — a modern, technical layout that "
        "demands precision.",
        "Traction out of the slow corners onto the straights is where the lap "
        "time lives here.",
        "A proper modern circuit — clinical, challenging and easy to lose time "
        "on.",
    ],
    "chang": [
        "The Chang International Circuit at Buriram — Thailand's flagship track, "
        "and brutally hot.",
        "Long straights and heavy braking zones make it a real slipstreaming "
        "venue.",
        "The heat here is a factor in itself — tyres and brakes take an "
        "absolute hammering.",
    ],
    "sachsenring": [
        "The Sachsenring — short, tight and twisty, a stronghold of "
        "motorcycle racing in eastern Germany.",
        "That long downhill Sachsenkurve is blind and committed — it takes "
        "real bravery.",
        "There's barely a breather on this lap; it's relentless from start to "
        "finish.",
    ],
    "raceroom": [
        "RaceRoom Raceway — the sim's own home circuit, a flowing fictional "
        "track with a bit of everything.",
        "A great all-rounder: quick sweepers, technical sections and a proper "
        "overtaking spot or two.",
        "It rewards a tidy, rhythmic lap more than outright bravery.",
    ],
    "mid-ohio": [
        "Mid-Ohio — a classic natural-terrain road course set in the rolling "
        "Ohio countryside.",
        "It's tight, narrow and technical, with the Keyhole and the Carousel "
        "among its signature corners.",
        "A long-time IndyCar and sportscar favourite where overtaking is at a "
        "real premium.",
        "The elevation and the lack of room make this a proper precision test.",
    ],
}

# WHERE THE LAP IS WON: the pundit's analytical coaching — where to find time,
# the key corners, the overtaking spots. Merged into the same picker as
# TRACK_FACTS (same keys), so mid-race the booth mixes history WITH genuinely
# useful "how to attack this place" insight. (This was the bit the player loved.)
TRACK_COACH = {
    "laguna": [
        "The lap here hinges on the Corkscrew — get a clean entry and you carry "
        "speed over the crest; commit too early and you wash wide on the plunge.",
        "Turn two and the Andretti hairpin are the real overtaking chances; the "
        "rest is too committed to dive down the inside.",
        "Laguna is a traction circuit — square off the slow corners, get the car "
        "rotated, and fire it out cleanly. That's where the time is.",
    ],
    "bathurst": [
        "Across the top of the mountain the time comes from sheer commitment — "
        "there's no room for error, so the ones who don't lift find the lap.",
        "Overtaking is all down Mountain Straight and into The Chase; the "
        "mountain itself is about rhythm and survival.",
        "A clean exit from the top sets up the whole run down Conrod — lose time "
        "up there and you pay for it all the way to the bottom.",
    ],
    "panorama": [
        "The mountain rewards bravery over the crests — find a rhythm across the "
        "top and the lap time follows.",
        "Your one big overtaking zone is the bottom of the mountain; everywhere "
        "else, patience is the only way through.",
    ],
    "spa": [
        "The middle sector is where Spa is won — those long flowing curves reward "
        "a settled car and a driver who trusts the front end.",
        "Your overtaking spots are the Bus Stop and the run up to Les Combes; "
        "nail the exit onto the straight and the slipstream does the rest.",
        "Eau Rouge isn't where you pass — it's where you set up everything after "
        "it. Commit through there and the whole lap opens up.",
    ],
    "monza": [
        "It's all about the chicanes — brake deep, get it turned, fire it out; "
        "the Lesmos and Parabolica reward patience on entry for speed onto the "
        "straights.",
        "Overtaking in a straight line is the easy part here; the art is "
        "defending into the first chicane without wrecking your exit.",
    ],
    "nurburg": [
        "Around the modern Grand Prix circuit the time is in the technical "
        "infield — traction and patience over outright bravery.",
    ],
    "nordschleife": [
        "You don't attack the Green Hell, you build up to it — find a rhythm, "
        "respect the blind crests, and the time comes from confidence.",
        "Knowing what's over each crest is worth more than horsepower here — "
        "commitment born of memory is the real lap time.",
    ],
    "suzuka": [
        "The Esses are where the lap lives — a rhythm section where momentum is "
        "everything; lose the front in the first and you pay all the way through.",
        "130R and the final chicane set up the run to the line — that's your "
        "overtaking window at Suzuka.",
    ],
    "imola": [
        "Time at Imola is in the chicanes — sharp, precise, kerb-riding stuff; "
        "Acque Minerali and the Variante Alta reward attacking the kerbs cleanly.",
        "It's a tough place to pass, so track position is gold — qualifying and "
        "the opening lap matter enormously around here.",
    ],
    "silverstone": [
        "Maggotts and Becketts is where the brave find their time — minimal "
        "steering, maximum commitment, carrying speed through the whole complex.",
        "Stowe and the Loop are your overtaking zones; a clean exit from Chapel "
        "gives you the run down the Hangar Straight.",
    ],
    "zandvoort": [
        "The banking lets you carry astonishing speed, but the lap time is in "
        "trusting it — commit to the banked corners and let the camber work.",
        "Passing is genuinely hard here, so a strong exit onto the main straight "
        "from that final banked turn is everything.",
    ],
    "brands hatch": [
        "Paddock Hill Bend is the signature — turn in almost blind over the crest "
        "and let it run down the hill; that's where the brave find time.",
        "Your best look is into Druids after the plunge down Paddock — get that "
        "hairpin right and you set up the whole lap.",
    ],
    "hockenheim": [
        "The stadium section is where the lap comes alive — tight and technical, "
        "the place to make up time after the fast run through the forest.",
    ],
    "red bull ring": [
        "Short lap, big stops — turns one, three and four are heavy braking zones "
        "and your best overtaking chances; nail the traction on exit.",
    ],
    "spielberg": [
        "It's a traction circuit — the time is all in firing cleanly out of the "
        "heavy braking zones and onto those uphill straights.",
    ],
    "interlagos": [
        "The climb to the line means a good exit from the final corner pays "
        "double; the Senna S is your main overtaking chance lap after lap.",
        "It's a momentum lap — the long left of Curva do Sol carries you onto the "
        "back straight, so protect that exit above all.",
    ],
    "watkins": [
        "The Esses reward commitment, and the Bus Stop is your overtaking chance "
        "— it's all about the drive onto the back straight.",
    ],
    "road america": [
        "Long straights and heavy braking — turns five and eight are the passing "
        "spots, and the time is all in nailing the exits onto those straights.",
    ],
    "indianapolis": [
        "On the road course the infield is fiddly and technical — patience there "
        "sets up the long runs where you actually find the lap time.",
    ],
    "daytona": [
        "On the banking it's momentum and the draft — both your lap time and your "
        "overtaking come from how cleverly you use the tow.",
    ],
    "le mans": [
        "Top speed down the Mulsanne matters, but the Porsche Curves are where a "
        "brave driver finds real time — flowing, committed, unforgiving.",
        "The two Mulsanne chicanes are your heavy braking zones and your best "
        "overtaking chances on that endless straight.",
    ],
    "hungaroring": [
        "With overtaking so hard, the whole lap is about track position — "
        "qualifying and the undercut decide races here.",
        "It's a rhythm circuit: link the turns smoothly, protect the front "
        "tyres, and never throw away the exit onto the main straight.",
    ],
    "zolder": [
        "The chicanes are the key — attack the kerbs to find time, but unsettle "
        "the car and you'll lose everything on exit.",
        "Carry your speed through the quick stuff; that's where the brave make "
        "the difference at Zolder.",
    ],
    "zhuhai": [
        "The long back straight and the heavy stop at the end are your big "
        "overtaking chance — it's all about the exit before it.",
        "Be patient through the technical middle sector; tidy lines there set "
        "up the whole lap.",
    ],
    "sonoma": [
        "The downhill esses are where the lap is won and lost — commit early, "
        "because there's no margin if you get it wrong.",
        "Elevation hides the apexes, so it's all about confidence and a clean "
        "drive out of the slow corners.",
    ],
    "sebring": [
        "Survival is half the battle on this bumpy concrete — keep the car off "
        "the worst of it and look after the tyres and brakes.",
        "The fast corners reward bravery, but it's tyre and brake management "
        "over the long run that decides Sebring.",
    ],
    "portim": [
        "Commit over the blind crests — the drivers brave enough to carry speed "
        "where they can't see the apex find all the time here.",
        "Protect your exits up and over those brows; momentum is everything on "
        "this rollercoaster.",
    ],
    "barcelona": [
        "It's a tyre-management track above all — abuse the fronts early and "
        "that final sector will punish you late on.",
        "The long run to turn one is the prime overtaking chance; everywhere "
        "else, track position is king.",
    ],
    "paul ricard": [
        "The Mistral straight with its chicane is your overtaking chance — it's "
        "all about the slipstream and the heavy braking zone.",
        "Stay off those painted run-offs; they look harmless but they'll rob "
        "you of grip and a chunk of lap time.",
    ],
    "norisring": [
        "It's stop-and-go — huge braking into the hairpins, then traction back "
        "out; look after those brakes over a stint.",
        "The grandstand hairpin is the overtaking spot, so a strong exit onto "
        "the straight before it is everything.",
    ],
    "salzburgring": [
        "It's flat-out and flowing — carry the speed through the fast stuff and "
        "save your big stop for the tight hairpin.",
        "With so little run-off, precision matters more than bravery here; a "
        "small error costs a big lap.",
    ],
    "macau": [
        "Lisboa is the one real overtaking chance — get a run out of the last "
        "corner and dive down the inside.",
        "Through the mountain section it's all about precision; clip a wall and "
        "your race is over in an instant.",
    ],
    "dubai": [
        "Link the esses cleanly and protect your exits onto the straights — "
        "rhythm is where the Dubai lap is found.",
        "It's a flowing circuit that rewards a smooth, tidy driver over a "
        "ragged, aggressive one.",
    ],
    "moscow": [
        "Late braking into the slow corners and strong traction out is the "
        "recipe; link the chicanes without unsettling the car.",
        "Protect your exits onto the straights — that's where the lap time "
        "lives here.",
    ],
    "anderstorp": [
        "That long airfield straight makes traction out of the final corner "
        "absolutely vital — the whole lap builds to it.",
        "Commit through the fast sweepers and square off the slow corners for "
        "a clean drive onto the straights.",
    ],
    "oschersleben": [
        "Rhythm through the linked corners is everything — there's nowhere to "
        "make up a big chunk, so a tidy lap wins out.",
        "Be patient into the hairpins; get them slowed and hooked up, then "
        "fire out cleanly.",
    ],
    "lausitz": [
        "On the road course it's late braking and traction out of the slow "
        "stuff; a clean exit onto the straights is the key.",
        "Two different disciplines in one lap — adapt from the banking to the "
        "fiddly infield and you'll find the time.",
    ],
    "slovakia": [
        "It's a momentum lap — lift rather than brake through the sweepers and "
        "trust the line to carry your speed.",
        "Protect every exit onto the straights; clean traction is where the "
        "Slovakia Ring rewards you.",
    ],
    "ningbo": [
        "Traction out of the slow corners onto the straights is the priority — "
        "it's a clinical, modern test of precision.",
        "Be smooth through the technical sections; this is a track where you "
        "lose time in dribs and drabs.",
    ],
    "chang": [
        "Long straights and big stops make the braking zones your overtaking "
        "spots — get the exit before them right and you'll pounce.",
        "Manage the heat above all; tyres and brakes fade fast here, so the "
        "smart drive comes good late on.",
    ],
    "sachsenring": [
        "The downhill Sachsenkurve is the signature — blind, committed, and the "
        "place that separates the brave from the rest.",
        "Get traction out of the slow corners; on a lap this short, every "
        "clean exit is precious.",
    ],
    "raceroom": [
        "It rewards a tidy, rhythmic lap — string the quick sweepers and the "
        "technical sections together and the time comes.",
        "There's a real overtaking spot or two if you're brave on the brakes; "
        "set it up with a good exit beforehand.",
    ],
    "mid-ohio": [
        "With overtaking so hard, track position is everything — the Keyhole "
        "is your best look, so set it up with a strong exit before it.",
        "It's a precision lap through the narrow, technical sections; commit "
        "through the Esses and protect every exit.",
    ],
}

# the pundit's conversational follow-up after the lead drops a track fact.
# GENERIC pool, deliberately VARIED (racing character / challenge, not just
# "history") so unrecognised tracks don't all sound the same. Recognised
# circuits get a SPECIFIC follow-up from TRACK_PUNDIT_BY_TRACK below.
TRACK_PUNDIT = [
    "It's a proper drivers' track, this — it'll reward the brave today.",
    "There's a rhythm to this place, and whoever finds it first controls the race.",
    "The quick corners here separate the confident from the careful, every time.",
    "Track position is gold around here — get ahead and make them work for it.",
    "You can lose the whole lap in a single greedy kerb at a place like this.",
    "It punishes a tidy mistake as much as a big one — concentration is everything.",
    "The surface will keep changing all race — reading that is half the battle.",
    "Whoever's smoothest through the technical stuff will be there at the end.",
    "It's the kind of layout where confidence builds lap on lap — momentum matters.",
    "Brave on entry, patient on exit — that's the recipe at a track like this.",
    "Tyre management is going to tell its own story before the flag here.",
    "There's overtaking to be had if you commit — this won't be a procession.",
    "The braking zones are where the moves will come, mark my words.",
    "Get the slow corners right and the rest of the lap just falls into place.",
]

# track-SPECIFIC pundit colour, keyed by a circuit-name substring (same scheme
# as TRACK_FACTS). Brett Calloway's take on what makes THIS place special — so
# every venue sounds different instead of "so much history" every single race.
TRACK_PUNDIT_BY_TRACK = {
    "laguna": [
        "The Corkscrew still gives me butterflies — blind over the crest, the road drops away, and you just have to commit.",
        "Nail the plunge through the Corkscrew and you've half-won the lap at Laguna Seca.",
    ],
    "bathurst": [
        "Across the top of the mountain there's barely a car's width — Bathurst takes real bravery.",
        "Down Conrod Straight with the wall right there — this place doesn't forgive a moment's lapse.",
    ],
    "panorama": [
        "Across the top of the mountain there's barely a car's width — Bathurst takes real bravery.",
        "The climb up the mountain and that flat-out drop down Conrod — there's nothing else like Bathurst.",
    ],
    "spa": [
        "Eau Rouge flat-out is one of the great tests in all of motorsport — your stomach's in your mouth.",
        "Through these Ardennes forests the weather can change end to end of the lap — Spa keeps everyone honest.",
    ],
    "monza": [
        "The Temple of Speed — you're never alone into the first chicane, the slipstream sees to that.",
        "Brake a fraction early for the Roggia and three cars come past — Monza is all about nerve.",
    ],
    "nordschleife": [
        "Seventy-three corners, mate — the Green Hell asks more of a driver than anywhere on earth.",
        "You don't conquer the Nordschleife, you survive it — every single lap is a negotiation.",
    ],
    "nurburg": [
        "The GP loop is deceptively technical — patience through the Mercedes Arena is what unlocks the lap.",
        "After all that history, the modern GP circuit is a precise, fiddly little test of discipline.",
    ],
    "suzuka": [
        "Those opening esses are a rhythm test like no other — get the first one right and they all flow.",
        "130R taken flat takes a special kind of commitment — Suzuka separates the great from the merely good.",
    ],
    "imola": [
        "Old-school and unforgiving — the kerbs at the Variante Alta will bite hard if you get greedy.",
        "Tamburello, Acque Minerali — Imola is a proper throwback, and it demands respect every lap.",
    ],
    "silverstone": [
        "Maggotts and Becketts at full noise is the finest sequence of corners in the world, no argument.",
        "The fast stuff at Silverstone rewards a brave, committed driver every single time.",
    ],
    "zandvoort": [
        "Those banked corners are unique — you carry so much speed through them it barely feels real.",
        "The dunes funnel the wind here — Zandvoort never gives you the same lap twice.",
    ],
    "brands hatch": [
        "Paddock Hill Bend, downhill and off-camber straight off the line — your heart's in your mouth every lap.",
        "Brands drops and climbs like a rollercoaster — it's a real test of car control.",
    ],
    "hockenheim": [
        "Through the stadium section the grandstands are right on top of you — the atmosphere is electric.",
        "Heavy braking into the hairpin is the big overtaking chance — Hockenheim rewards a late lunge.",
    ],
    "red bull ring": [
        "Short but brutal on the brakes — those uphill stops really punish a tired car late on.",
        "Three big braking zones and not much else — at the Red Bull Ring it's all about traction up the hill.",
    ],
    "spielberg": [
        "Short but brutal on the brakes — those uphill stops really punish a tired car late on.",
        "Up and down the hillside with huge braking zones — Spielberg is a sprinter's track.",
    ],
    "interlagos": [
        "Down into the Senna S the whole place comes alive — and it runs anti-clockwise, hard on the neck all race.",
        "Interlagos is bumpy, old-school and always delivers drama — the crowd here is something else.",
    ],
    "watkins": [
        "The Esses flow beautifully, but it's the Bus Stop where races at the Glen are won and lost.",
        "Watkins Glen rewards commitment through the quick stuff — lift too early and you're swallowed up.",
    ],
    "road america": [
        "Long and fast — Road America is a top-speed track, but those heavy stops test the brakes to the limit.",
        "Four miles of flowing Wisconsin countryside — slipstream battles into the heavy braking zones are guaranteed.",
    ],
    "indianapolis": [
        "A century of history at the Brickyard, but on the road course it's the twisty infield that decides it.",
        "Part banked oval, part technical infield — Indianapolis asks two completely different things of a driver.",
    ],
    "daytona": [
        "The banking and the draft — at Daytona you're never truly clear of the car behind you.",
        "On the high banks it's all about the tow — get it wrong and the whole pack reels you straight back in.",
    ],
    "le mans": [
        "I've won here, and I'll tell you — the Porsche Curves at night are about as good as racing ever gets.",
        "Down the Mulsanne you've got time to think, and that's when the doubts creep in. Le Mans is mental as much as physical.",
    ],
    "hungaroring": [
        "Monaco without the walls — it's relentless, and overtaking is at an absolute premium.",
        "It's hot, dusty and physical here; track position is worth its weight in gold.",
    ],
    "zolder": [
        "Quick and sandy, this — you've got to trust the front end through the fast stuff.",
        "The chicanes make or break the lap at Zolder. Kerb them, but don't get greedy.",
    ],
    "zhuhai": [
        "That long back straight is the big opportunity — get the exit before it right and you're alongside.",
        "It's a proper test of a complete lap; the technical middle sector is where the time hides.",
    ],
    "sonoma": [
        "All elevation and commitment, Sonoma — those downhill esses give you nowhere to hide.",
        "Wine country it may be, but this place bites — blind, off-camber, and utterly unforgiving.",
    ],
    "sebring": [
        "That bumpy old airfield concrete shakes the cars to bits — survive Sebring and you can survive anywhere.",
        "It's as physical as racing gets; the cars and the drivers take an absolute pounding here.",
    ],
    "portim": [
        "A rollercoaster, Portimão — you're committing over blind crests with no sight of the apex. Pure faith.",
        "The elevation changes here are like nowhere else; it takes real bravery to attack them.",
    ],
    "barcelona": [
        "Everyone knows this place from testing, but that abrasive surface still punishes anyone who abuses the tyres.",
        "That final sector has ended a thousand good laps — it's where Barcelona really tests you.",
    ],
    "paul ricard": [
        "Those painted run-offs look harmless but they're lethal to your grip — stay on the black stuff.",
        "The Mistral straight with that chicane is the overtaking chance; it's all about the slipstream here.",
    ],
    "norisring": [
        "Stop, go, stop, go — the Norisring is all heavy braking and traction, a real brake-killer.",
        "It's the spiritual home of the DTM, and that grandstand hairpin always serves up drama.",
    ],
    "salzburgring": [
        "Fast and narrow in that Austrian valley — there's barely any run-off, so you'd better mean it.",
        "It's flat-out and flowing until that tight hairpin; commitment is everything here.",
    ],
    "macau": [
        "Lisboa is the big overtaking spot, but that mountain section is barely wider than the car. Terrifying.",
        "Macau has made and broken careers — there is simply no margin for error on these streets.",
    ],
    "dubai": [
        "A flowing modern circuit, this — under the floodlights it's got a real atmosphere of its own.",
        "It rewards a driver who can link the esses cleanly; rhythm is the key at Dubai.",
    ],
    "moscow": [
        "Flat and technical — it's late braking into the slow corners and traction back out that wins this.",
        "Linking those chicanes without unsettling the car is where the Moscow lap is found.",
    ],
    "anderstorp": [
        "That huge airfield back straight makes traction out of the final corner absolutely vital.",
        "A real 1970s throwback — flat, fast and unique. The flying Swede Ronnie Peterson loved it here.",
    ],
    "oschersleben": [
        "Tight and technical — it's a touring car classic where rhythm beats outright bravery.",
        "There's nowhere to make up a big chunk here; clean exits onto the short straights are everything.",
    ],
    "lausitz": [
        "Part oval, part infield — it asks two completely different things of a driver in one lap.",
        "This is where Zanardi showed the world what courage really means. A special place.",
    ],
    "slovakia": [
        "A momentum circuit, this — lift rather than brake through the sweepers and trust the line.",
        "Long and flowing, the Slovakia Ring; it rewards a driver who can carry speed.",
    ],
    "ningbo": [
        "Clinical and modern — traction out of the slow corners onto the straights is the priority.",
        "It's an easy place to lose a tenth; precision through the technical stuff is everything.",
    ],
    "chang": [
        "The heat at Buriram is a factor all on its own — tyres and brakes take a real hammering.",
        "Long straights and big stops make it a slipstreamer's track; get the exits right and you'll pounce.",
    ],
    "sachsenring": [
        "That downhill Sachsenkurve is blind and committed — it's a real test of nerve.",
        "Short, tight and relentless; there's barely a breather anywhere on this lap.",
    ],
    "raceroom": [
        "The sim's own home track — a flowing all-rounder with a bit of everything in it.",
        "It rewards a tidy, rhythmic lap; string it together and the time comes.",
    ],
    "mid-ohio": [
        "Tight, narrow and natural-terrain — Mid-Ohio is a precision test where track position is gold.",
        "The Keyhole and the Carousel define the lap; overtaking here is genuinely hard-won.",
    ],
}

# colour co-commentator follow-ups, grouped so the banter fits the moment
PUNDIT_LINES = {
    "overtake": [
        "Oh, that is brilliant racecraft.",
        "He had that planned two corners earlier, no doubt about it.",
        "Beautifully judged — never lifted.",
        "That's the move of the race so far for me.",
        "Cold as ice under braking there.",
        "He committed the moment he saw the gap — no hesitation.",
        "That takes real bottle, a move like that.",
        "Textbook. You couldn't coach it any better.",
        "He'd been setting that up for two laps, you could tell.",
        "The patience first, then the pounce — that's world-class racecraft.",
        "A decisive move, and beautifully clean with it.",
        "Inches in it. Millimetres. Absolutely stunning under pressure.",
        "No half measures — in and past before anyone had time to blink.",
        "The commitment level there is extraordinary.",
        "Perfect use of the slipstream — timed to the absolute millisecond.",
        "That's what separates the good from the great — reading the situation.",
        "Gone before the other driver even knew what was happening.",
        "A proper racing driver's move, that — brave and precise in equal measure.",
        "He saw the gap, he trusted himself, and he went for it. Simple as.",
        "Not everyone would try that at this stage of the race. He did. Brilliant.",
        "Committed all the way to the apex — the car responds and he's through. Sensational.",
        "You can't teach that. It's pure instinct — and it's worked perfectly.",
        "A controlled, well-thought-out pass — no contact, no drama. Classy.",
        "Outstanding depth of commitment into the braking zone — a genuinely great move.",
        "Two drivers. One gap. One committed. That's motor racing distilled.",
    ],
    "spin": [
        "Heartbreak — and it was all going so well.",
        "Just asked a bit too much of the rear there.",
        "That's a weekend unravelling in a single corner.",
        "Costly. Hugely costly.",
        "One moment of inattention and it's all undone — motor racing can be so cruel.",
        "The rear stepped out and there was simply nothing to be done about it.",
        "That mistake is going to be replayed many times tonight. Tough one.",
        "Desperately harsh for them — a single error and the race has gone.",
        "The tyres were talking to them, and they didn't listen until it was too late.",
        "A real shame — they were building something good out there.",
        "Overcooking it into the corner and paying a very heavy price.",
        "Every racing driver's nightmare — losing it when everything was going right.",
        "That's the thing about motor racing — one lapse in concentration and it's over.",
        "Trying to find time that wasn't there — and it's cost them enormously.",
        "The circuit got them in the end. It happens to everyone here.",
        "A moment of oversteer that turned into a full pirouette. Absolutely gutting.",
        "Overambitious at the worst possible moment — and now they're picking up the pieces.",
        "You can be the best driver in the world and this track will still bite you.",
        "Snap oversteer — no time to correct it. Pure misfortune.",
        "Ambition and rubber came to a disagreement. The rubber won.",
        "They were SO much quicker just then — and this happens. Brutal sport.",
        "Went for everything and got nothing. Motor racing is rarely fair.",
        "The heart says push; the tyres said no. An argument they could not win.",
    ],
    "leadchange": [
        "And just like that, the complexion of the race changes.",
        "The lead was always going to be on borrowed time.",
        "You could see that coming for a couple of laps.",
        "This race has a new protagonist — fascinating.",
        "The momentum has completely shifted at the front.",
        "That is the pivotal moment of this race right there.",
        "Everything changes. EVERYTHING. That's a lead change.",
        "I said the pressure would tell — and there it is.",
        "The leader at the front is not the story anymore.",
        "This is what makes racing the greatest sport in the world.",
        "A new name at the top, and we are absolutely nowhere near done.",
        "You build a lead and then in one move it's gone — dramatic doesn't cover it.",
        "The race just flipped completely. The maths has changed for everyone.",
        "Bold move. Perfectly executed. A lead change that could decide everything.",
        "From one leader to another in the blink of an eye. Sensational.",
        "The running order rewritten — and the script has been torn up with it.",
        "Every pitstop, every move — it led to that. A defining lead change.",
        "This race has found its most important moment. Right there.",
        "The chess match has reached its king move. A lead change at the front.",
    ],
    "win": [
        "A thoroughly deserved victory, that.",
        "Controlled from the front — a masterclass.",
        "They'll remember this one for a long time.",
        "Utterly dominant. Start to finish. Wow.",
        "A perfect race. You can't say fairer than that.",
        "I said before the start they had the pace — they had the RACE.",
        "From the moment the lights went out, this was always going to be their day.",
        "Not a single fault. Not one. A flawless performance.",
        "An extraordinary display of racecraft from start to chequered.",
        "The best driver today won. It really is as simple as that.",
        "Composed, clinical, and classy. A champion's performance.",
        "Nobody was touching them today — a drive completely in a class of its own.",
        "You love to see raw talent converted into a result that clean.",
        "There will be some very happy people in that garage tonight.",
        "That victory was earned over every single lap, from the very beginning.",
        "Pace. Control. Nerve. They had it all today — a magnificent win.",
        "Poetry in motion, that performance. From first corner to last.",
        "I've seen some drives here over the years. That belongs near the top.",
        "When the history of this race is written, today's winner is going to feature prominently.",
    ],
    "battle": [
        "This is racing at its absolute finest.",
        "Wheel to wheel and not giving an inch.",
        "Edge of your seat stuff, this.",
        "Hard but fair — exactly how it should be.",
        "Neither of them willing to blink first.",
        "This is what we came to see, right here.",
        "Respect between them, but no quarter given.",
        "Two of the best drivers on this grid and they both know it.",
        "You'd frame this if you could — genuine wheel-to-wheel racing.",
        "Neither is going to give it up easily. This could run all day.",
        "The bravery on display here is just remarkable.",
        "When you see racing like this, you remember why you love the sport.",
        "The lines they're choosing, the braking points — everything on the razor's edge.",
        "The crowd must be absolutely electric for this one.",
        "Pure heart, pure determination, pure racecraft — everything you want from motorsport.",
        "I am leaning forward in my chair, I can tell you that.",
        "Nose to tail, line to line — you could not put a credit card between them.",
        "No team orders, no politics, no strategy — just two drivers settling it on track.",
        "This is the kind of battle that defines careers and creates legends.",
        "Absolutely no intention of conceding from either side — this is thrilling.",
        "If you had to show someone what motor racing IS, it would be this.",
        "Both committed, both brave, both absolutely convinced they can win this.",
        "The gearbox ratios, the fuel load, the tyre condition — everything matters in this fight.",
        "Hard but brilliant — the kind of battle that gets talked about in pubs for years.",
        "Neither driver is giving the other a centimetre. Magnificent racing.",
    ],
    "penalty": [
        "Self-inflicted, that one. They'll be kicking themselves.",
        "The stewards had no choice there, really.",
        "That's going to undo a lot of hard work.",
        "A time penalty — and that completely changes their afternoon.",
        "The stewards have been watching that all race, I think.",
        "Once they reviewed the footage, there was only one outcome.",
        "That'll drop them back down the order significantly.",
        "A harsh call, perhaps, but the rule is the rule.",
        "They'll be furious in the garage, but they brought it on themselves.",
        "A drive-through — or equivalent — and their race is compromised.",
    ],
    "yellow": [
        "Safety first — let's hope everyone's okay.",
        "This could shake up the order, mind you.",
        "Eyes up through there, it can catch you out.",
        "Yellow flags mean one thing: someone is in trouble out there.",
        "Double yellows — you have to lift and hold your position.",
        "A crucial moment now — a yellow here can change everything.",
        "All eyes on the pit wall as those yellow flags go up.",
        "The timing of this yellow is going to be really significant.",
        "You cannot overtake under yellows — and the stewards WILL be watching.",
        "This could be a pivotal moment in the race, right here.",
        "Every team on the pit wall recalculating their strategy right now.",
    ],
    "late": [
        "We're into the final stages now — every lap is crucial.",
        "{togo} laps to go. The pressure is building with every passing corner.",
        "The end game begins — {togo} laps remaining.",
        "Time is running out for anyone looking to make a move.",
        "The race is entering its defining phase right now.",
        "With {togo} laps left, this is where championships are won and lost.",
        "The fuel is going light and the tyres are going away — perfect storm.",
        "Hearts are pounding in the garages — {togo} laps to go.",
        "Squeaky-bum time now — {togo} laps and the nerves are jangling.",
        "{togo} to run, and nobody can afford a single mistake.",
        "This is the business end — {togo} laps to decide it all.",
        "The closing laps, and you can cut the tension with a knife.",
        "{togo} laps remaining, and it's all still to play for up there.",
        "We're in the endgame now — {togo} laps, hold it together.",
        "Crunch time — {togo} laps left and every corner matters.",
    ],
    "final_lap": [
        "THIS IS IT — the FINAL LAP! Who takes the glory?",
        "Last lap! Everything decided in the next few minutes!",
        "One lap left — and what a race it's been!",
        "Final lap, ladies and gentlemen — we're nearly there!",
        "HERE WE GO — one last lap to settle it all!",
        "The chequered flag awaits — final lap underway!",
        "Last lap! Hold your nerve and hold your line!",
        "This is the one that counts — final lap, all or nothing!",
        "One more time around — who wants it most?!",
        "The bell lap! Empty the tank, leave nothing out there!",
        "Final tour — and the tension is absolutely unbearable!",
        "Last lap drama incoming — buckle up!",
        "We're down to the last lap and it is on a knife edge!",
        "Final lap! Whatever happens now, what a way to finish!",
    ],
    "generic": [
        "Superb stuff.",
        "The crowd are on their feet.",
        "You don't see many better than that.",
        "This race has a bit of everything.",
        "Absolutely loving this one.",
        "What a way to spend an afternoon.",
        "Pure theatre, this race.",
        "You couldn't ask for more, could you.",
        "Top-drawer entertainment.",
        "That's racing at its very best.",
        "Edge-of-your-seat stuff, this.",
        "You can't take your eyes off it.",
        "Brilliant from start to finish.",
        "This is why we love the sport.",
        "Sensational. Just sensational.",
        "Wheel-to-wheel and no quarter given — magnificent.",
        "The standard out there is exceptional.",
        "Bottle that and sell it — what a contest.",
        "Goosebumps, honestly. What a race.",
        "Drama at every turn here.",
        "They're putting on a show for us today.",
    ],
}

# free-flowing booth analysis for the quiet moments (keeps the conversation going)
ANALYSIS_LINES = [
    "Tyre management is going to decide this one in the closing laps.",
    "The pace at the front has been relentless all afternoon.",
    "Watch the gaps here — a single mistake and it all changes.",
    "Track position is everything around {trk}.",
    "The leaders are managing this beautifully so far.",
    "It's the consistency that's impressing me today.",
    "There's a real chess match developing through the field.",
    "Keep an eye on that battle further back, it's heating up.",
    "Brake temperatures will be a real concern in this phase of the race.",
    "It's all about who can keep their tyres alive to the flag now.",
    "The dirty air is making it so hard to follow closely through here.",
    "You can see them saving the tyres for one last push.",
    "Whoever times their move best is going to come out on top here.",
    "The margins are absolutely tiny at this level — fractions of a second.",
    "Concentration is everything now; one lapse and it's all over.",
    "This is the part of the race where experience really tells.",
    "The track's evolving lap by lap, more grip coming all the time.",
    "A few of these drivers are starting to feel the pressure now.",
    "It's a war of attrition out there — patience will be rewarded.",
    "The strategists on the pit wall will be working overtime right now.",
    "Confidence is high through the quick stuff — they're really committing.",
    "Small lock-ups creeping in; the tyres are clearly going off.",
    "The undercut is alive and well here — track position is gold.",
    "You can almost hear the tyres screaming for mercy out there.",
    "It's fascinating watching the different lines drivers are trying.",
    "Fuel saving may come into play in these middle laps, mark my words.",
    "The wind has picked up, and that's unsettling the cars through the quick corners.",
    "Some are nursing it home, others are still attacking — a real contrast.",
    "Reading the gaps tells you everything about who's struggling out there.",
    "The racing line is a metre wide and they're hitting it every single lap.",
    "Track temperature climbing — that'll hurt the cars running soft tyres.",
    "It's a thinking driver's race, this — brains as much as bravery.",
    "A yellow flag now would throw the whole strategy into chaos.",
    "Those running in clean air have a real advantage at the moment.",
    "Every overtake costs tyre life — they have to pick their moments.",
    "The braking zones are where this race is being won and lost.",
    "You sense someone is about to roll the dice on strategy here.",
    "The leaders have a rhythm now — it'll take something special to break it.",
    "Watch the body language of the cars — that's where the clues are.",
    "This is the phase where a race quietly slips away from you.",
    "Consistency over heroics — that's what wins races like this.",
    "There's grip coming to the circuit by the lap, and the times reflect it.",
    "A long, long way to go, and plenty of twists left in this tale.",
    "The thing that separates the great races from the good ones is moments — and we're building them.",
    "Psychology plays a massive part in the closing stages; who blinks first loses.",
    "Tyre degradation is the great leveller — no amount of raw pace covers it.",
    "The overtaking opportunities here are few and far between — every attempt must count.",
    "There's a real craft to following without overtaking — keeping the pressure applied.",
    "Air temperature dropping — that'll bring the tyres in from the cold. Changes everything.",
    "It's a fine line between preservation and pace, and very few can walk it.",
    "Strategy is crystallising now — the teams have committed to their choices.",
    "The fuel load is lightening every lap, and the fastest cars will start to show themselves.",
    "Passing here is so difficult — track position is worth more than an extra tenth a lap.",
    "Whoever manages the middle sector best is going to be the one smiling at the end.",
    "The smallest set-up detail can unlock half a second at {trk} — it's that precise.",
    "Mental strength is tested when the tyres go away and the gap stays big.",
    "I always say the race is won in the middle: neither the start nor the finish, the laps between.",
    "The cars ahead are being chased hard — but the chasing requires tyre expenditure too.",
    "Every lap here is a calculated risk. The best drivers calculate perfectly.",
    "Watch the exit speeds from this complex — that's where time is made or lost.",
    "An aggressive strategy from one team could yet overturn everything we think we know.",
    "The question on everyone's lips: do the tyres last, or will someone blink and box early?",
    "Pit stop timing windows are opening and closing, lap by lap, corner by corner.",
    "If you'd left after the first lap, you'd have missed everything — this race has depth.",
    "Risk and reward: every lap out on old rubber is a gamble on a safer strategy.",
    "The data is telling interesting stories on those pit walls — teams adapting in real time.",
    "Physical fitness matters as much as car setup now — the drivers will be feeling every bump.",
    "Sector three is where the tyre degradation really bites at {trk} — watch for the slide.",
    "This circuit rewards drivers who trust the rear, and punishes those who don't.",
    "The pace is incredible — lap times barely fluctuating. Precision engineering and skill.",
    "Patience is a weapon, and some are deploying it brilliantly right now.",
    "A race that refuses to settle — every time you think the order is fixed, something shifts.",
    "The tyres are the story of every race at {trk} — the cliff edge is always near.",
    "Watching the fastest laps tick by tells you who is in trouble and who has more in reserve.",
    "Five things could change this race in the next few laps: strategy, tyres, incidents, errors, and nerves.",
    "Every driver in that field has spent years preparing for moments exactly like this.",
    "Nobody is coasting — even the comfortable leaders are working hard to stay comfortable.",
    "The mechanics of racing: the harder you push, the faster the tyres go — and the gap shrinks.",
    "One yellow, one spin, one gamble — and this leaderboard resets entirely.",
    "What's fascinating is not who's fastest, but who's managing the fastest pace longest.",
    "There are no hiding places at {trk} — the circuit demands honesty from every car.",
    "The gaps are small because the talent is enormous. Everyone here is the real deal.",
    "Two-stopping and trying to make it work, or one-stopping and managing — that is the question.",
    "When you race here, the margin for error narrows with every passing lap.",
    "Momentum is a commodity, and some drivers are spending it very wisely.",
    "Position, pace, and preservation — the three P's that decide every race at this level.",
    "The clock is the invisible opponent — it never gets tired, never makes mistakes.",
    "Watching the gap evolution over ten laps tells you the whole strategic story.",
    "Some drivers are like sharks — utterly patient, waiting for the moment to arrive.",
    "Energy management, mental management, tyre management — the modern racing driver does it all.",
    "When the race is this close, luck and preparation both play their role. Equally.",
]
# the booth's race-filler "analysis" category pulls from the pool above (the
# engine calls L("analysis", ...) -> COMMENTARY_LINES["analysis"]); wire it in
# so those 43 lines actually get used instead of silently no-op'ing.
COMMENTARY_LINES["analysis"] = ANALYSIS_LINES

# late-phase urgency + final-lap calls (the lead commentator). These are fired
# via L("late") / L("final_lap"); they belong in COMMENTARY_LINES (a near-
# identical set also exists in PUNDIT_LINES for the pundit's follow-up banter).
COMMENTARY_LINES["late"] = [
    "We're into the final stages now — every lap is crucial.",
    "{togo} laps to go. The pressure is building with every passing corner.",
    "The end game begins — {togo} laps remaining.",
    "Time is running out for anyone looking to make a move.",
    "The race is entering its defining phase right now.",
    "With {togo} laps left, this is where it's won and lost.",
    "The tyres are going away and the tension is rising — {togo} to go.",
    "Squeaky-bum time now — {togo} laps remaining.",
]
COMMENTARY_LINES["final_lap"] = [
    "THIS IS IT — the FINAL LAP! Who takes the glory?",
    "Last lap! It all gets decided right here!",
    "One lap left — and what a race it's been!",
    "Final lap, ladies and gentlemen — we're nearly there!",
    "HERE WE GO — one last lap to settle it all!",
    "The chequered flag awaits — final lap underway!",
]

# ---- INSIGHT: the pundit's "meaning" layer ------------------------------------
# Unlike ANALYSIS_LINES (generic colour), these are filled from the LIVE race
# state — the actual front gap, laps remaining, the podium margin — and framed
# so the viewer understands the race AS A WHOLE: what a gap is worth, what's at
# stake, whether the race is breaking open or still alive. The engine
# (_insight) decides which category genuinely applies right now, then fills the
# numbers. Placeholders: {p1} {p2} {p3} leaders' names, {gap} a spoken gap
# ("under a second" / "1.8 seconds"), {togo} laps remaining, {total} race laps.
COMMENTARY_LINES["insight_lead_slim"] = [
    "Just {gap} between {p1} and {p2} with {togo} laps to run — this win is far from decided.",
    "{p1} leads, but only by {gap} — and with {togo} laps left, {p2} is well within range.",
    "This is a proper contest for the win: {gap} the margin, {togo} laps to settle it.",
    "{p2} is shadowing {p1} by {gap}, and there are {togo} laps left to find a way through.",
    "The leader has no breathing room — {gap} back to {p2}, {togo} laps of pressure to come.",
    "{gap} covers the top two with {togo} to go — one slip from {p1} and this flips.",
    "Don't look away: {p1} and {p2} split by just {gap}, {togo} laps of tension ahead.",
    "The fight for the lead is alive — {gap} between {p1} and {p2}, {togo} laps to run.",
    "{togo} laps left and only {gap} at the front. This is exactly the race we wanted.",
    "{p1} can't relax for a second — {p2} is right there, {gap} adrift with {togo} to go.",
    "A slender {gap} is all {p1} has over {p2}, and {togo} laps is plenty of time to lose it.",
    "This one's going to the wire — {gap} the gap, {togo} laps to decide who wins it.",
]
COMMENTARY_LINES["insight_lead_big"] = [
    "{p1} has broken the back of this — {gap} clear, and now it's a race for the minor places.",
    "The lead is commanding: {gap}. Barring disaster, {p1} has this one in hand.",
    "{p1} has checked out — {gap} up the road. The real racing is now the fight behind.",
    "A {gap} cushion for {p1} — that's a lead built on consistency, lap after lap.",
    "Behind {p1}'s {gap} advantage, the scrap for second is where the action is now.",
    "{p1} is in cruise control — {gap} clear and managing it with complete ease.",
    "{gap} is a lifetime at this stage — {p1} can look after the tyres and the pace from here.",
    "The leader has stretched it to {gap}; this becomes a contest for the remaining podium steps.",
    "{p1} has turned this into a procession out front — {gap} the margin and growing.",
    "Twelve corners of perfection have given {p1} a {gap} lead — that's a masterclass.",
]
COMMENTARY_LINES["insight_podium_fight"] = [
    "The final podium place is under siege — just {gap} covers it.",
    "{p3} is clinging to that last podium spot by {gap}, and it will not be comfortable.",
    "Watch the fight for third: {gap} the margin, and a trophy on the line.",
    "P3 is where the drama is — {gap} between a podium and heartbreak.",
    "{gap} for the final podium step — this is the battle to keep your eyes on.",
    "Someone's going home with a trophy and someone isn't — and {gap} decides it.",
    "The last place on the rostrum is wide open — {gap} covers it right now.",
    "{p3} can hear the footsteps — {gap} is all that protects that podium.",
    "A podium hangs on {gap} — third place is anything but settled.",
]
COMMENTARY_LINES["insight_field_spread"] = [
    "The leaders have gone clear — the best racing now is in the heart of the field.",
    "Forget the front for a moment; the midfield is where the real scrapping is.",
    "This has split into separate races — a leader alone, and a pack squabbling behind.",
    "The front runners have stretched out, so the entertainment is back in the pack.",
    "It's become a procession at the front, but the midfield is anything but settled.",
    "The race has broken into pockets — keep your eyes on the battles through the order.",
    "Up front it's strung out, but dive into the midfield and it's wheel to wheel.",
]
# a flurry of positions changing at once — a pile-up or multi-car melee (common
# in online races). The pundit flags the chaos. No names (it's the whole pack).
COMMENTARY_LINES["shuffle"] = [
    "Ooh, and there's a big shuffle in the order back there!",
    "Lots of positions changing all at once — something's happened in the pack!",
    "A real shake-up in the order — places changing hands all over the shop!",
    "Whatever just happened, the order's been turned upside down!",
    "Big movement through the field — a whole flurry of position changes!",
    "That's shuffled the pack right up — several places swapping at once!",
    "Chaos through the order — a cluster of position changes there!",
    "The order's just been scrambled — lots of cars on the move!",
]

# ---- RACE ARC: callbacks to a driver's earlier incident -----------------------
# Fired later in the race for a driver who had an early off/big loss (a "spun"
# story tag): did the incident cost them (still well down), or did they bounce
# back (recovered to/above their grid slot)? {drv} = the driver.
COMMENTARY_LINES["arc_cost"] = [
    "That earlier incident has really cost {drv} — still well down on where they started.",
    "You can see the damage from {drv}'s earlier moment — they never recovered the lost ground.",
    "{drv} is still paying for that earlier off — a race that rather got away from them.",
    "That early mistake proved expensive for {drv} — down below their grid slot now.",
    "A shame for {drv} — that earlier incident has defined their whole afternoon.",
    "{drv} just hasn't been able to claw back what that earlier moment cost them.",
    "The early trouble for {drv} is still telling — a long road back from that one.",
]
COMMENTARY_LINES["arc_recovered"] = [
    "Credit to {drv} — they haven't let that earlier incident affect their race at all.",
    "{drv} has put that early moment completely behind them — right back in the mix.",
    "What a response from {drv} — recovered everything they lost earlier, and then some.",
    "You'd never know {drv} had that earlier off — they've clawed it all back.",
    "Real character from {drv}, bouncing back strongly from that early setback.",
    "{drv} refused to let that earlier incident derail them — a superb recovery.",
    "That early trouble looked costly, but {drv} has answered it brilliantly.",
]

# ---- RacerTV channel identity: self-aware booth flavour -----------------------
# Delivered by the lead commentator as occasional mid-race colour — channel IDs,
# the RaceRoom/RacerTV in-world framing, a bit of humour and sarcasm, and light
# ribbing of the pundit by name. This is what sells RacerTV as its own thing.
COMMENTARY_LINES["broadcast"] = [
    "You're watching RacerTV, the only channel brave enough to cover this lot.",
    "RacerTV — bringing you every bump, scrape and optimistic overtake in RaceRoom.",
    "Quick reminder you're locked onto RacerTV, where the racing's real and the budget isn't.",
    "If you've just joined us here on RacerTV, you've picked a good one.",
    "This is RacerTV — accept no substitutes. Mainly because there aren't any.",
    "RaceRoom serving up another cracker, and RacerTV has every angle covered.",
    "{pundit} and I will guide you through it — this is RacerTV, after all.",
    "RacerTV: proudly sponsored by absolutely no one, and loving it.",
    "Stay right here on RacerTV — {pundit} promises me it gets even better.",
    "That's the sort of move that keeps RacerTV in business, eh {pundit}?",
    "Another day at the RacerTV office, and {pundit} has already spilled his coffee.",
    "You won't see racing like this anywhere else — and trust me, we checked.",
    "RacerTV, your home of RaceRoom racing — and home to {pundit}'s questionable hot takes.",
    "Apparently our RacerTV ratings spike every time someone goes off. No pressure, drivers.",
    "Welcome back to RacerTV, where {pundit} and I argue and the cars do the talking.",
    "RacerTV's been on air for, ooh, the whole afternoon now — and what an afternoon.",
]

# ---- OFF-TRACK incidents: the PUNDIT's domain ---------------------------------
# He reports the moment it happens (the engine interrupts whatever's playing).
# Deliberately GENERIC — never states HOW (no "spun", "clipped the kerb",
# "oversteer"); too specific breaks immersion and is often wrong. Just: someone
# has gone off. {drv} = the driver.
# NAMED follow-up, said AFTER the instant bridging sting — so it's the detail,
# in PAST tense (the moment has already happened by the time the name lands).
# {drv} = the driver. Reads naturally on its own too, for the cold-start case
# where the sting cache isn't ready yet.
COMMENTARY_LINES["offtrack"] = [
    "That was {drv} who went off there — a real shame.",
    "It was {drv}, off the track and losing ground.",
    "{drv} was the one who ran wide there — costly.",
    "That's {drv} who went off — dropping places as we speak.",
    "{drv} went off the circuit there — a big moment.",
    "It's {drv} in trouble — off the track and recovering.",
    "{drv} ran wide and went off — let's hope there's no damage.",
    "That was a mistake from {drv}, off the track there.",
    "{drv} went off there — that's going to hurt their race.",
    "It was {drv} off the road — a real setback.",
    "{drv} the driver who went off — scrambling to recover now.",
    "That was {drv}, off the track and places tumbling away.",
    "{drv} went off there — they'll rejoin well down the order.",
    "It's {drv} who's gone off — a costly error.",
    "That was {drv} who ran wide and lost it there.",
    "{drv} went off the track there — a tough moment for them.",
]
# PAST-TENSE naming of who went off, used as the follow-up to a yellow (the
# report may land a beat late, so past tense keeps it immersive). {drv} = culprit.
COMMENTARY_LINES["offtrack_late"] = [
    "Looks like it was {drv} involved in that earlier incident.",
    "And it seems {drv} was the one caught up in that.",
    "That looked like {drv} in the middle of it.",
    "I think that was {drv} who went off there.",
    "Replays suggest {drv} was the one in trouble.",
    "{drv} the driver who came off worst in that, by the look of it.",
    "From what we can see, it was {drv} who ran into bother there.",
    "That'll have been {drv}, by the looks of it — off the track.",
]
# the FRESH off-track call when it CUTS OFF the other voice mid-sentence — the
# pundit apologises for jumping in (a natural broadcast interruption). {drv}=car.
COMMENTARY_LINES["offtrack_cut"] = [
    "Sorry to cut you off, but {drv} has just run wide!",
    "Apologies for interrupting — {drv} has gone off!",
    "Sorry to jump in, but {drv} is off the track!",
    "Forgive me cutting in — {drv} has run wide!",
    "Sorry, I have to stop you there — {drv} has gone off!",
    "Excuse the interruption — {drv} is off the road!",
    "Sorry to break in, but {drv} has gone off!",
    "Let me jump in there — {drv} has run wide and gone off!",
    "Hold that thought — {drv} is off the track!",
    "Sorry to interrupt, but there's trouble — {drv} has gone off!",
    "Sorry to cut across you {comm}, but {drv} has gone off!",
    "Forgive me {comm} — {drv} has just run wide!",
    "Hold on {comm}, we've got drama — {drv} is off!",
]
# a SECOND car going off while the pundit is still reporting the first — folded
# in as a follow-up (queued behind, never cuts the first call off). {drv} = car.
COMMENTARY_LINES["offtrack_more"] = [
    "And {drv} is off as well — more drama!",
    "More trouble! {drv} has gone off too!",
    "{drv} joins them off the track!",
    "And there's another — {drv} is off!",
    "Make that two — {drv} has gone off as well!",
    "{drv} is off too! It's all happening out there!",
    "And now {drv} as well — off the road!",
    "{drv} has gone off behind them — what a moment!",
]
# THREE or more going off in a burst — one summarising 'chaos' line (no name),
# then we stay quiet so it never turns into a spammy roll-call.
COMMENTARY_LINES["offtrack_chaos"] = [
    "It's chaos out there — several cars off the track!",
    "Carnage! Multiple cars have gone off!",
    "This is bedlam — cars going off all over the place!",
    "Mayhem out there — a whole cluster of cars off the road!",
    "What is going on?! Several drivers off the track at once!",
    "It's all kicking off — multiple cars in trouble!",
]
# the lead commentator's brief, warm acknowledgement after the pundit calls an
# off-track (a natural booth hand-back — "thanks for that, hope they're okay").
COMMENTARY_LINES["offtrack_ack"] = [
    "Thanks for that — let's hope they're okay.",
    "Good spot. Hopefully no harm done.",
    "Thanks. Fingers crossed there's no damage.",
    "Appreciate it — a shame to see, hope they recover.",
    "Thanks for flagging that. Hope they're back going soon.",
    "Noted — let's hope it's nothing serious.",
    "Cheers for that. A tough break for them.",
    "Thanks. Hopefully they can get it going again.",
    "Good eye. Let's hope they're alright.",
    "Thanks for that. Racing can be cruel sometimes.",
    "Indeed — hope they can rejoin without too much lost.",
    "Thanks. Not what they needed at all.",
    "Thanks {pundit} — let's hope they're okay.",
    "Good spot, {pundit}. Hopefully no harm done.",
    "Cheers {pundit}. A rotten bit of luck, that.",
    "Thanks for that, {pundit} — eyes peeled for the replay.",
]
# MODERATE off — the driver ran wide / had a moment but kept it going. Lighter
# than the dramatic 'offtrack' report; names {drv}.
COMMENTARY_LINES["ranwide"] = [
    "{drv} runs wide there and bleeds a bit of time — gathers it back up, though.",
    "A moment for {drv} — out onto the run-off, but no harm done.",
    "{drv} gets it a touch wrong and runs wide — that'll have cost a tenth or two.",
    "Wide goes {drv}! Ran out of road there but keeps it pointing the right way.",
    "{drv} overcooks the entry and takes to the escape road — recovers nicely.",
    "Bit untidy from {drv} there — wheels off the track, a small moment.",
    "{drv} runs deep and drops a wheel or two off — loses a fraction but stays in it.",
    "A scruffy one for {drv} — ran wide, scrubbed some speed, back on now.",
    "{drv} pushes a little too hard and runs wide — gathers it, no real damage.",
    "Off-line and onto the dirty stuff for {drv} — a moment, but they hang on.",
    "{drv} misses the apex and sails wide — that's time lost out there.",
    "Half a spin avoided by {drv} — ran wide, caught it, carries on.",
]
COMMENTARY_LINES["insight_time_left"] = [
    "Around {mins} minutes left on the clock — the race enters its final phase.",
    "{mins} minutes to go — this is where the timed races are won and lost.",
    "Just {mins} minutes remaining, and it's all still to play for.",
    "The clock shows about {mins} minutes left — decision time is approaching.",
    "{mins} minutes on the clock — whatever's going to happen needs to happen soon.",
    "We're inside the final {mins} minutes now — every lap counts from here.",
    "About {mins} minutes left — the timing screens will be everything now.",
]
COMMENTARY_LINES["insight_laps_left"] = [
    "{togo} laps to go — this is where races are won and lost.",
    "We're into the business end now: {togo} laps left to settle everything.",
    "{togo} of {total} laps remaining, and the picture is still taking shape.",
    "Decision time is approaching — {togo} laps left for someone to make a move.",
    "{togo} laps to run, and every single one of them matters from here.",
    "The clock is ticking down: {togo} laps left to change the story of this race.",
    "Only {togo} laps left now — whatever's going to happen has to happen soon.",
    "{togo} laps remain — the margin for error shrinks with each one.",
]

# the lead commentator's reply after the pundit gives his analysis (a hand-off,
# so it actually sounds like a two-way conversation rather than two monologues)
CROSSTALK_ACK = [
    "That's an interesting take. Let's see how this race plays out.",
    "Thanks for that input from our analysis team trackside.",
    "Great insight, as always. Back to the action.",
    "Couldn't agree more — let's see if you're right.",
    "Good point, well made. We'll keep an eye on that.",
    "Fascinating stuff. Plenty still to come, then.",
    "Thanks for the analysis — now, back to the racing.",
    "Spot on, I think. And there's the action to prove it.",
    "Hard to argue with that. Let's see if the drivers agree.",
    "A really shrewd observation. We'll come back to it, no doubt.",
    "That's why you're the expert. Right, back to the track.",
    "Well put. There's a lot riding on exactly that.",
    "I had a feeling you'd say that — and you may well be right.",
    "Noted. Let's keep our eyes peeled for it, then.",
    "Brilliant analysis. The race just keeps on giving.",
    "Great insight as always, {pundit}. Back to the action.",
    "Thanks {pundit} — spot on, I reckon.",
    "Hard to argue with that, {pundit}. Let's see if the drivers agree.",
    "That's why you're here, {pundit}. Right, back to the track.",
]

# the pundit's answers when the lead commentator asks him a question
CROSSTALK_ANSWERS = [
    "Well {comm}, {drv}'s looking really strong out there.",
    "Good question, {comm} — for me it's {drv} who's the standout.",
    "I'll tell you what, {comm}, the tyres are going to decide this one.",
    "Funny you ask, {comm} — {drv} is the one quietly nailing it.",
    "{drv}'s looking really strong, genuine composure out there.",
    "Honestly, {drv} has been one of the standouts — so tidy and precise.",
    "I'd keep a close eye on {drv}, building into this really nicely.",
    "Tyre management is the key, and {drv} is nailing it so far.",
    "It's finely poised, but for me {drv} has just got the edge.",
    "{drv}'s race pace has been the story of the day, no question.",
    "Early days, but {drv} looks like the one to beat from here.",
    "There's more to come from {drv}, I'm certain of that.",
    "Well, it all comes down to those final laps, doesn't it.",
    "For me it's about who keeps their head when it matters most.",
    "I think the tyres are the great equaliser here, no doubt about it.",
    "Honestly, I wouldn't want to call this one — it's that close.",
    "The one to watch is {drv}, quietly putting together a brilliant race.",
    "Whoever's brave enough through the quick stuff wins this, simple as that.",
    "I'd say {drv} has the measure of the field on pace right now.",
    "It's finely balanced, but momentum is with {drv} for me.",
    "{drv} is reading the race beautifully — always in the right place.",
    "What impresses me is {drv}'s patience; never forcing it.",
    "If anyone's going to crack the order open, it's {drv}.",
    "{drv} has that rare gift of looking quick without looking rushed.",
    "I keep coming back to {drv} — the most complete performance out there.",
    "It hinges on the tyres, and {drv} is treating them with real care.",
    "{drv} is the value pick for me — flying under the radar today.",
    "You can't teach what {drv} is showing us — pure racing instinct.",
    "There's a steeliness to {drv} today that the others just don't have.",
    "Watch the in-laps and out-laps — that's where {drv} is gaining.",
    "For me {drv} has more in reserve than anyone realises.",
    "The composure of {drv} under this pressure is genuinely special.",
    "Strategy will decide this as much as pace — the pit wall may be the difference.",
    "I keep asking myself: where does the tyre life end? And the answer isn't yet.",
    "A fascinating strategic subplot has been building — I think it comes to a head soon.",
    "The driver I'd want on my side right now is {drv} — complete package.",
    "Tyre temperatures are going to be critical through that final complex.",
    "This is where you earn your reputation as a great racer — these closing stages.",
    "The mental side is massive — keeping focus when the tyres and the gap are marginal.",
    "I'd say this race still has three or four genuinely pivotal moments left in it.",
    "The battle for second place might matter more than the lead right now — pace-wise.",
    "A fascinating chess match — every team on the pit wall has multiple scenarios running.",
    "I trust the tyres to last. But only just. And that 'just' is what makes racing great.",
    "{drv} has been exceptional at managing traffic on the in- and out-laps.",
    "What you're seeing from {drv} right now is genuine racecraft — not just speed.",
    "The track is rubbering in nicely on the racing line — but everywhere else is treacherous.",
    "Seven out of ten for the racing. The final laps will decide if it goes to a ten.",
    "The gap between intent and execution is where races are won — {drv} is bridging it.",
    "Whoever blinks first in this strategic game could lose the whole afternoon.",
    "The fine detail — the millimetre brake points, the fraction-earlier throttle — that's the difference.",
    "I've watched a lot of racing here, and this has all the ingredients of something special.",
    "There's latent drama in every gap on that timing screen — it just hasn't detonated yet.",
    "Confidence. Commitment. Control. The three things winning drivers have that others don't.",
    "You cannot underestimate the energy a fresh set of tyres gives a driver's mindset.",
    "The race narrative is building towards a climax — I can feel it.",
    "A properly compelling midrace — strategy, battles, unknowns everywhere.",
    "Every great race needs a second act, and I think we're right in the middle of it.",
    "The talent in this field is extraordinary — it makes every position fight a pleasure.",
    "You forget how physically brutal racing is — the drivers are working as hard as the engineers.",
]

# TRACK-SPECIFIC booth lore, keyed by circuit-name substring (same scheme as
# TRACK_FACTS). MILES (lead, F1 World Champion turned rally) recalls his title
# battles with Schumacher/Barrichello/Häkkinen at the great F1 venues; BRETT
# (pundit, Le Mans / WEC champion) drops easter eggs about the endurance greats
# he raced — Kristensen, McNish, Pirro, Lotterer, Capello. Picked by _lore_answer
# when the booth's racing-past banter lands on a circuit we have a memory for.
LORE_COMM_BY_TRACK = {            # Miles' F1-champion-then-rally memories
    "spa": [
        "Spa? I won here the year I took the title — hauled it through Eau Rouge flat with Mika Häkkinen's mirrors full of me. You never forget a lap like that.",
        "I love this place. Schumacher and I went side by side up through Raidillon once, neither lifting. Bravest thing I ever did in a car.",
    ],
    "monza": [
        "Monza! I clinched a championship here, slipstreaming Schumacher to the line into the Parabolica. The tifosi nearly brought the grandstands down.",
        "I out-dragged Barrichello to the flag through these Lesmos once — by a car length. The Temple of Speed gave me one of my greatest days.",
    ],
    "silverstone": [
        "Silverstone's my back garden — I won my home Grand Prix here, wheel to wheel with Rubens through Becketts. Best day of my career, bar none.",
        "Maggotts and Becketts at full chat against Häkkinen — that's as alive as I ever felt in a racing car.",
    ],
    "suzuka": [
        "Suzuka decided my title one year — me and Schumacher nose to tail through the esses, neither of us breathing. Ice in the veins, that's what it took.",
        "130R in my day was properly frightening, flat out with Mika alongside. This place sorts the brave from the rest, always has.",
    ],
    "imola": [
        "Imola — we raced hard here in my F1 days, wheel to wheel with Häkkinen into Tamburello. A circuit that demanded total respect, and still does.",
        "I won here once managing the car to the flag while Schumacher chewed his tyres up behind. Patience took that one.",
    ],
    "interlagos": [
        "Interlagos! I came from nowhere to win here in the wet — Barrichello chasing me the whole way, the crowd roaring for him. Pure magic.",
        "Anti-clockwise, bumpy, hard on the neck — I took a title down to the wire here against Mika. Loved every second.",
    ],
    "hungaroring": [
        "Budapest — I won here from the second row, couldn't pass Schumacher for thirty laps until he finally blinked. Patience won me that one.",
        "Monaco without the walls, this — I learned to bide my time here, then pounce. Beat Häkkinen to the flag doing exactly that.",
    ],
    "hockenheim": [
        "Hockenheim, the old long blast through the forest — I out-dragged Häkkinen to the line here for a famous win. Proper old-school racing.",
        "Into that stadium section with Schumacher alongside and ninety thousand Germans screaming for him — you don't forget that.",
    ],
    "nurburg": [
        "The Nürburgring — I sealed a title here once, holding off Schumacher when the rain came down. Kept my head while others lost theirs.",
        "This GP loop is fiddlier than it looks. I beat Rubens here by reading the weather better than he did.",
    ],
    "barcelona": [
        "Barcelona — endless testing in my F1 days, then I won the race too, nursing the tyres while Rubens cooked his. Knowledge is everything here.",
        "That final sector cost Häkkinen a win against me once — he ran wide, I pounced. This place punishes the smallest greed.",
    ],
    "zandvoort": [
        "Zandvoort — those banked corners were a thrill even in my F1 car. I won here side by side with Mika through Tarzan. Wonderful place.",
    ],
    "red bull ring": [
        "The old Österreichring up here was lightning fast — I took a win battling Schumacher up and down this hillside. Brakes glowing every lap.",
    ],
}
LORE_PUNDIT_BY_TRACK = {          # Brett's Le Mans / WEC memories
    "le mans": [
        "Le Mans — I won it twice, you know. Three in the morning down the Mulsanne, Tom Kristensen's headlights filling my mirrors. Nothing on earth like it.",
        "The Porsche Curves at night, flat out, McNish a length behind — that's the greatest thing I ever did in a racing car.",
    ],
    "spa": [
        "Spa? The Six Hours here is a monster — I diced with Allan McNish through Eau Rouge in the wet once, two prototypes inches apart. Terrifying and glorious.",
        "I love this place. Kristensen and I raced wheel to wheel up through Raidillon in an LMP1 car — your heart's in your mouth the whole way.",
    ],
    "sebring": [
        "Sebring! Twelve hours on that brutal concrete — McNish and I beat each other senseless over the bumps. I still feel it in my back today.",
        "Survive Sebring and you can survive anything. Pirro and I dragged two broken cars to the flag here once, refusing to give in.",
    ],
    "bathurst": [
        "Bathurst — I did the 12 Hour across that mountain. Wheel to wheel over the top of it, barely a breath the whole lap. Daunting place.",
        "Down Conrod with the wall right there and a rival alongside — Bathurst is as committed as racing gets.",
    ],
    "nurburg": [
        "The Nürburgring 24 — a full day and night around the Green Hell. I shared a car with André Lotterer once; that man is from another planet.",
        "Twenty-four hours here strips you bare. I've raced the very best around this place and lived to tell it.",
    ],
    "nordschleife": [
        "The Nordschleife in the dark, in the rain — I did the 24 Hours here with Lotterer. Seventy-three corners you cannot see. Pure faith.",
        "You don't conquer the Green Hell, you survive it. I battled McNish through here once — two madmen in the fog.",
    ],
    "daytona": [
        "Daytona, the Rolex 24 — round the banking in the dark, drafting Emanuele Pirro hour after hour. Endurance racing strips you to nothing.",
        "Twenty-four hours on the high banks — I raced Kristensen here, neither of us willing to lift in the draft. Madness.",
    ],
    "monza": [
        "Monza in a prototype — the speed down those straights is frightening. I raced Dindo Capello here, the two of us refusing to lift into the Parabolica.",
        "The Six Hours of Monza — I slipstreamed McNish to the line into the first chicane once. Sportscars at this place are something else.",
    ],
    "silverstone": [
        "Silverstone hosted some great WEC rounds — I went toe to toe with Kristensen through Maggotts in an LMP1 car. Heart-in-your-mouth stuff.",
        "Six hours here in a prototype — I diced with McNish through Becketts lap after lap. Proper, honest racing.",
    ],
    "interlagos": [
        "São Paulo in the WEC — bumpy, anti-clockwise, brutal on the neck for a stint. I loved every minute of battling McNish here.",
    ],
    "sonoma": [
        "I raced sportscars across these Californian hills — wheel to wheel with Pirro down through the esses. No margin anywhere.",
    ],
}

# NAMED corners in TRACK ORDER, keyed by a circuit-name substring. The overlay
# learns each track's corner POSITIONS from the speed trace (universal "Turn N"),
# then upgrades the number to a real name using these ordered lists — but ONLY
# when the count of detected corners closely matches the list length, so a
# mismatch can never produce a confidently-wrong name (it just stays "Turn N").
# These are the SLOW, speed-dipping corners a driver actually brakes for, in lap
# order (flat-out kinks are not separate detections). Best-effort; the named
# overlay is conservative by design.
CORNER_NAMES = {
    "laguna": ["Andretti Hairpin", "Turn 2", "Turn 3", "Turn 4", "Turn 5",
               "Turn 6", "the Corkscrew", "Rainey Curve", "Turn 10", "Turn 11"],
    "spa": ["La Source", "Eau Rouge", "Les Combes", "Malmedy", "Rivage",
            "Pouhon", "Fagnes", "Stavelot", "the Bus Stop"],
    "monza": ["the first chicane", "Curva Grande", "the Roggia chicane",
              "Lesmo 1", "Lesmo 2", "Ascari", "Parabolica"],
    "silverstone": ["Abbey", "Village", "the Loop", "Brooklands", "Luffield",
                    "Copse", "Maggotts", "Becketts", "Stowe", "Vale", "Club"],
    "suzuka": ["the first corner", "the esses", "Dunlop", "Degner",
               "the hairpin", "Spoon", "the chicane"],
    "imola": ["Tamburello", "Villeneuve", "Tosa", "Piratella", "Acque Minerali",
              "the Variante Alta", "Rivazza"],
    "zandvoort": ["Tarzan", "Gerlach", "Hugenholtz", "Hunzerug", "Rob Slotemaker",
                  "Scheivlak", "Masters", "the Audi chicane", "Arie Luyendyk"],
    "brands hatch": ["Paddock Hill Bend", "Druids", "Graham Hill Bend",
                     "Surtees", "Hawthorn", "Westfield", "Sheene", "Clearways"],
    "interlagos": ["the Senna S", "Curva do Sol", "Descida do Lago",
                   "Ferradura", "Laranja", "Pinheirinho", "Bico de Pato",
                   "Mergulho", "Juncao"],
    "red bull ring": ["Turn 1", "the Remus hairpin", "Turn 3", "Turn 4",
                      "the Rauch", "Turn 6", "the Rindt"],
}

# PAIRED crosstalk: the lead asks a SPECIFIC question and the pundit gives a
# matching answer. The old system picked the answer from one flat pool regardless
# of the question, so "rate them out of ten" got answered with "the tyres will
# decide it" — a non-sequitur. Here each topic keeps its question and answer pools
# together so the exchange actually makes sense. {drv}/{pos} = the driver in
# question; general topics ignore them. CROSSTALK_ANSWERS (above) stays as a
# safe fallback if a topic is ever missing.
CROSSTALK = {
    # rate a driver out of ten — answer gives a number + justification
    "rate": {
        "q": [
            "How would you rate {drv}'s afternoon so far out of ten, {pundit}?",
            "Put a number on {drv}'s drive for me, {pundit} — out of ten?",
            "Out of ten, what's {drv}'s race been worth so far?",
        ],
        "a": [
            "I'd give {drv} a solid eight — composed, quick, barely a wheel out of place.",
            "Eight, maybe a nine. The only thing missing for {drv} is the result to cap it off.",
            "A seven from me — quick, but {drv} has left a touch on the table in a couple of corners.",
            "Honestly? A nine. {drv} has been just about flawless out there today.",
        ],
    },
    # is tyre life the story — answer is about deg / management
    "tyres": {
        "q": [
            "Are the tyres going to be the story of this race, {pundit}?",
            "Is this one going to come down to tyre life, do you think?",
            "How big a factor are the tyres going to be from here?",
        ],
        "a": [
            "No question — whoever looks after their rubber best wins this. The deg is brutal.",
            "Absolutely. The fronts are going off a cliff, and the driver who manages that takes it.",
            "It will. We'll see who's truly saved their tyres when the last few laps come around.",
            "For me, yes — the track temp is high and the rears won't last. Management is everything.",
        ],
    },
    # the podium scrap — answer is about that fight
    "podium_fight": {
        "q": [
            "What's your read on the battle for the podium, {pundit}?",
            "How do you see this podium fight shaking out?",
            "Who's winning that scrap for the rostrum, do you think?",
        ],
        "a": [
            "It's the best fight on track — three cars covered by a second and none giving an inch.",
            "Whoever's bravest into the final sector takes that last podium step. It's knife-edge.",
            "Track position is everything now — clean air there is worth half a second a lap.",
            "Tyres decide it. The one who saved a set earlier grabs that podium late on.",
        ],
    },
    # the standout / unsung driver — answer names {drv}
    "standout": {
        "q": [
            "Who's the standout performer for you so far, {pundit}?",
            "Who's quietly having the best race that nobody's talking about?",
            "Give me the name that's impressed you most out there, {pundit}.",
        ],
        "a": [
            "{drv}, without a doubt — flying under the radar, but the lap times are right there.",
            "For me it's {drv}. Not flashy, just relentlessly quick and never a mistake.",
            "{drv}. Came through traffic, kept it clean, and is reeling them in up front.",
            "It has to be {drv} — making the tough overtakes look completely routine.",
        ],
    },
    # where the race is won and lost — answer is a place on the track
    "won_lost": {
        "q": [
            "Where's this race being won and lost for you, {pundit}?",
            "Where does this one actually get decided, do you reckon?",
            "What's the key part of the lap in this one, {pundit}?",
        ],
        "a": [
            "Through the middle sector — that's where the brave ones are finding half a second.",
            "On the brakes into the final hairpin. Get it right, you're through; wrong, you're in the wall.",
            "On the in- and out-laps. Whoever nails the undercut window wins this race.",
            "Traction out of the slow corners. The car that hooks up there just pulls clear.",
        ],
    },
    # can they hold the position — answer is yes/tight/if
    "hold_on": {
        "q": [
            "Has {drv} got enough in hand to hold on, do you think?",
            "Can {drv} make P{pos} stick from here, {pundit}?",
            "Is {drv} going to keep that position to the flag?",
        ],
        "a": [
            "I think so — {drv} has managed the gap perfectly, always responding when it's needed.",
            "It'll be tight. {drv} is hanging on, but the tyres are fading and the pressure's building.",
            "If {drv} keeps it clean, yes. One mistake, though, and that door swings wide open.",
            "Just about. {drv} has the pace; it's the nerve in the closing laps that gets tested.",
        ],
    },
    # is a pass coming — answer is about the overtake
    "move_on": {
        "q": [
            "Is there a move on the cards for {drv}, do you reckon?",
            "Can {drv} find a way past from there, {pundit}?",
            "Is {drv} going to make that overtake stick?",
        ],
        "a": [
            "Oh, it's coming — {drv} is all over the back of that car and only needs one clean run.",
            "Down the inside into Turn 1, surely. {drv} has the better exit every single lap now.",
            "Not yet — {drv} needs to get closer through the last corner first, then it's on.",
            "I'd say so. {drv} is quicker; it's just a matter of when, not if.",
        ],
    },
    # pit-wall message — answer is the advice you'd give
    "pitwall": {
        "q": [
            "What would you be telling {drv} on the radio right now, {pundit}?",
            "If you were on {drv}'s pit wall, what's the message?",
            "What's the call to {drv} from the pit wall here, {pundit}?",
        ],
        "a": [
            "Two words: heads down. {drv} has the pace — just keep banking the laps.",
            "I'd tell {drv} to look after the front-left and stay patient. The chance will come.",
            "Push now. {drv} has a tyre advantage and this is the window to use it.",
            "Calm and steady. {drv} doesn't need heroics, just clean laps to the flag.",
        ],
    },
    # is the pressure telling — answer is about composure
    "pressure": {
        "q": [
            "Is the pressure starting to tell on {drv}, do you think?",
            "How's {drv} handling the pressure out there, {pundit}?",
            "Are the nerves getting to {drv} at all from what you can see?",
        ],
        "a": [
            "Not a flicker so far — {drv} is ice-cool, hitting the same marks every lap.",
            "You can see it building. {drv} ran a fraction wide last time through; the cracks may show.",
            "Brilliantly. The closer it gets, the calmer {drv} seems to drive — that's rare.",
            "It's a real test. {drv} has a car right in the mirrors and absolutely nowhere to hide.",
        ],
    },
    # prediction for the finish — answer is a forecast
    "prediction": {
        "q": [
            "Where do you see this one finishing up, then, {pundit}?",
            "Give me your prediction, {pundit} — how does this race end?",
            "Call it for me, {pundit}: how does this one finish?",
        ],
        "a": [
            "I think it goes down to the final lap — far too close to call right now.",
            "The leader holds on, but it'll be by less than a second, mark my words.",
            "Expect late drama. These tyres won't make the finish without a real fight.",
            "I reckon we see one more big move before the flag. This one is not done yet.",
        ],
    },
}

# the colour man's reaction lines used in the post-race wrap-up
PUNDIT_SUMMARY = [
    "Wow, that really was a thrilling race. Hats off to {p1}, a brilliant drive.",
    "Cracking stuff from start to finish. {p1} thoroughly deserved that one.",
    "What a show that was. {p2} and {p3} can be proud of the podium too.",
    "Brilliant racing all afternoon — {p1} was just that bit too good today.",
    "That's right up there with the races of the season for me. Bravo, {p1}.",
    "{p1} managed that to perfection — but spare a thought for {p2}, so close.",
    "A proper contest from green to chequered. {p1} the deserved winner.",
    "You couldn't script it better. {p1} on top, {p2} and {p3} pushing to the end.",
    "Hats off to all three — {p1}, {p2} and {p3} gave us a real treat today.",
    "{p1} delivered when it mattered, and that's the mark of a class act.",
]

# the pundit's immediate take on the WINNER, used early in the post-race
# conversation (right after the lead commentator's win call) so the wrap-up
# actually plays as a back-and-forth between the two of them.
PUNDIT_WINNER = [
    "Absolutely, and what made the difference for {p1} was the consistency — never put a wheel wrong.",
    "Spot on. {p1} controlled that beautifully, exactly when the pressure was highest.",
    "No arguments here — {p1} had the measure of this field all afternoon.",
    "Yes, and you have to say {p1} earned every bit of that. A complete drive.",
    "Couldn't agree more. {p1} just had that little bit extra when it counted.",
    "Indeed — {p1} made the tough part look routine, and that's the hallmark of a winner.",
    "Totally deserved. {p1} kept their head while others lost theirs.",
    "Right you are — {p1} judged the whole race to perfection.",
    "It was a masterclass from {p1}, no question about it.",
    "And the brilliant thing, {p1} always seemed to have an answer when challenged.",
]

# the pundit's "driver of the race" — congratulates the winner, then singles out
# a standout drive from P2-P5 ({pick}) the way a real analyst picks a man of the
# match. Used right after the lead calls the win.
PUNDIT_PICK = [
    "Very good from {p1}. For me though, the standout was {pick} — strong race pace, kept their head down.",
    "A deserved win for {p1}. But I really enjoyed watching {pick} — great pace, no mistakes all afternoon.",
    "Hard to fault {p1}. For me, {pick} was the one to watch, though — quietly brilliant out there.",
    "Lovely from {p1}. My driver of the race? {pick}. Patient, quick, and kept it clean.",
    "Top drawer from {p1}. But keep an eye on {pick} — that was a really mature drive.",
    "Credit to {p1}. For me, {pick} caught the eye — strong pace and lovely racecraft.",
    "{p1} thoroughly deserved it. My pick of the day, though, is {pick} — superb under pressure.",
    "No arguments about {p1}. Although {pick} impressed me most — clean, quick, composed.",
    "Great stuff from {p1}. Personally, I loved {pick}'s race — head down, no fuss, real speed.",
    "Fine win for {p1}. But the drive of the day for me was {pick} — quietly excellent.",
]
