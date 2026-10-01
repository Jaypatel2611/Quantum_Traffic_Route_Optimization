# SIH26137 Demo Video Script (about 3 minutes)

## Why the video is built this way
- Judges care about new ideas, a working build, real impact, a clear demo, and a finished product. A working demo beats pretty slides ([how I won SIH](https://blogs.reskilll.com/how-i-won-smart-india-hackathon-lessons-36-hours-changed-everything/), [what judges look for](https://blogs.reskilll.com/what-hackathon-judges-look-for-complete-judging-criteria-breakdown-2026/)).
- Short (about 3 minutes), real product, real data, show the result first.
- Other teams on this problem show a map, a chart and a comparison. We also show: real roads, many accidents at once, what each accident did, and our CO2/fuel numbers with the assumptions in the open.
- We could not find public SIH demo videos for this problem. The order below comes from winner write-ups.

## Script

| Time | What is on screen | What to say |
|---|---|---|
| 0:00-0:15 | Title: team, SIH26137, project name. Then the Setup screen with the city map. | "Delivery trucks waste time and fuel on bad routes. Our tool plans the routes, shows them on real roads, and shows what accidents do to them." |
| 0:15-0:35 | Pick the city. The real road map is there. Upload the CSV (or use the demo one). Move the mouse over a few dots. | "Pick a city and the real roads load. Every stop from your file is a dot. Hover on a dot to see its name, how much it needs, and where it is." |
| 0:35-1:00 | Click **Inject Accidents**. Click two roads, one by one. Red dashed lines appear and a list shows both. Remove one, add it again. | "Now we add accidents. Click any road. It turns red and goes on the list. You can add many, remove one, or clear all." |
| 1:00-1:25 | Click **Run Optimization**. Live screen: chart moving, two solver cards. Point at the greyed Back button. | "Two solvers plan the same trucks: OR-Tools, the industry standard, and our quantum-inspired one, QPSO. Same data, same time limit, same random seed, so it is a fair test. While it works, Back is switched off so nothing gets lost." |
| 1:25-2:05 | Results screen. Routes follow the streets. Point at the yellow parts and the red roads. Click the vehicle buttons to show one truck at a time. Scroll to the route list. | "Routes follow real streets, not straight lines. Red roads are the accidents. Yellow shows where a route had to go around one. Pick any truck to see only its path. Below, each truck's exact order: depot, stop, stop, depot, with each stop's demand, distance and time." |
| 2:05-2:30 | Scroll to the **Accident impact** and **Effect on route order** boxes. | "For each accident we say what happened: it did not touch any route, the truck went around it and lost this many minutes, or there was no way around and it drove through slowly. We also say if the order of stops changed, and if that change really saved time." |
| 2:30-2:50 | Click **View Green Impact**. Open the assumptions box. | "Here are the CO2, fuel and time numbers, with the assumptions open so anyone can check them. On this small case both solvers find the same plan, so the difference is zero. On bigger cases the numbers show the real gap, good or bad." |
| 2:50-3:00 | Click Back to show the work is kept. Closing card with GitHub and team. | "Go back at any time and nothing is lost. Runs on a normal laptop, offline, on real Indian roads. Thank you." |

## Short 30-second version
Hook (0:00), accidents turning red (0:35), routes on real streets with the truck buttons (1:25), the impact boxes (2:05), closing card.

## Say it honestly
- Say: "quantum-inspired". It runs on a normal computer. It is not a quantum computer.
- Do not say QPSO beats OR-Tools. On our tests it ties on the smallest case and is behind OR-Tools on bigger ones (15 stops: slightly behind, 30 stops: well behind, 60 stops: behind). Our strength is the clear, explainable search and the tools around it, not winning.
- If a judge asks about quality, say: "OR-Tools is our benchmark. We match it on small cases and we report the gap on big ones."
- Only say numbers that are on the screen in your recording.
- Do not talk about companies, cloud or paid plans here. That belongs in the slides.

## Before you record
1. Start the backend (port 8000) and the frontend (port 4173). Open the app at `localhost:4173`, not `127.0.0.1`.
2. Run `npm run build` in `frontend` first so the screen has the latest changes.
3. Use the built-in 5-stop demo (2 trucks, capacity 100). It finishes in about 10 seconds. Practise once and keep the best take.
4. Click slowly on roads: move the mouse onto a road, wait one second, then click. A very fast click can be missed.
5. After Results opens, wait 5-10 seconds: the "Effect on route order" box first says "Comparing…" and then fills in.
6. Record at 1080p, zoom the browser to 110-125%, hide bookmarks. Record the voice separately so the sound is clean.
