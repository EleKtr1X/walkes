<script lang="ts">
	import mbgl, { type GeoJSONSource } from 'mapbox-gl';
	const { Map, GeolocateControl } = mbgl;
	import 'mapbox-gl/dist/mapbox-gl.css';
	import { onDestroy, onMount } from 'svelte';
	import { PUBLIC_MAPBOX_GL, PUBLIC_SERVER_URL } from '$env/static/public';
	import type { GeoJSON } from 'geojson';

	let { data }: { data: GeoJSON } = $props();

	let map: mapboxgl.Map;
	let mapContainer: HTMLElement;
	let geo: mapboxgl.GeolocateControl;

	let lat = $state(43.4697944);
	let lng = $state(-80.5537445);
	let zoom = $state(15);
	let showOptions = $state(false);
	let submitted = $state(false);
	let submitting = $state(false);
	let timer: NodeJS.Timeout | undefined = $state();

	onMount(() => {
		map = new Map({
			container: mapContainer,
			accessToken: PUBLIC_MAPBOX_GL,
			center: [lng, lat],
			zoom: zoom,
			style: 'mapbox://styles/mapbox/dark-v11'
		});

		geo = new GeolocateControl({
			positionOptions: {
				enableHighAccuracy: true
			},
			trackUserLocation: true,
			showUserHeading: true
		});

		map.addControl(geo);

		map.on('load', async () => {
			if (timer) {
				clearInterval(timer);
			}

			geo.trigger();

			geo.on('geolocate', ({ coords }) => {
				lat = coords.latitude;
				lng = coords.longitude;
			});

			map.addSource('segments', {
				type: 'geojson',
				data: data
			});

			map.addLayer({
				id: 'segments-layer',
				type: 'line',
				source: 'segments',
				paint: {
					'line-color': [
						'interpolate',
						['linear'],
						['get', 'risk_score'],
						0.0,
						'#00c853',
						0.5,
						'#ffd600',
						1.0,
						'#d50000'
					],
					'line-width': 3
				}
			});

			timer = setInterval(async () => {
				const res = await fetch(`${PUBLIC_SERVER_URL}/segments`);
				const data: GeoJSON = await res.json();

				if (map.style) {
					const source: GeoJSONSource | undefined = map.getSource('segments');
					if (source) {
						source.setData(data);
					}
				}
			}, 10000);
		});
	});

	onDestroy(() => {
		if (map) {
			map.remove();
		}
		if (timer) {
			clearInterval(timer);
		}
	});

	function reportClick() {
		showOptions = !showOptions;
	}

	async function reportHazard(condition: string) {
		submitting = true;

		const res = await fetch(`${PUBLIC_SERVER_URL}/report`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				condition,
				lat,
				lng
			})
		});

		submitting = false;
		if (!res.ok) {
			alert(`ERROR ${res.status}: ${res.statusText}`);
		} else {
			submitted = true;
			setTimeout(() => {
				submitted = false;
				showOptions = false;
			}, 5000);
		}
	}
</script>

<div class="absolute h-full w-full" bind:this={mapContainer}></div>

<div class="absolute top-5 left-5 flex flex-col">
	<div class="mb-2 flex flex-row items-center gap-1 text-3xl font-bold text-white">
		<i class="ti ti-walk"></i>
		<span>Walkes</span>
	</div>
	<div class="flex flex-row items-center gap-2 rounded-t-xl bg-white px-3 pt-2 pb-1 text-lg">
		<i class="ti ti-current-location"></i>
		<input type="text" placeholder="Starting point" />
	</div>
	<div class="flex flex-row items-center gap-2 rounded-b-xl bg-white px-3 pt-1 pb-2 text-lg">
		<i class="ti ti-map-pin"></i>
		<input type="text" placeholder="Destination" />
	</div>
	<button
		class="mt-2 flex cursor-pointer flex-row items-center
                 justify-center gap-1 rounded-xl bg-blue-600 py-2 text-2xl font-bold text-white hover:brightness-80"
	>
		<i class="ti ti-walk"></i>
		Go!
	</button>
</div>

<div class="absolute right-5 bottom-10 flex flex-col items-end gap-4">
	{#if showOptions}
		<div class="flex flex-row gap-3 rounded-2xl bg-gray-700 p-6">
			{#if submitted}
				<span class="text-white">Thank you for contributing!</span>
			{:else if submitting}
				<i class="ti ti-loader text-white"></i>
			{:else}
				<div class="flex flex-col items-center justify-center gap-1">
					<button
						class="bottom-10 h-16 w-16 cursor-pointer rounded-full
                        bg-white text-2xl font-bold text-white hover:brightness-80"
						onclick={() => reportHazard('snow')}
						title="Snow/Ice"
					>
						<i class="ti ti-snowflake text-black"></i>
					</button>
					<span class="text-white">Snow/Ice</span>
				</div>
				<div class="flex flex-col items-center justify-center gap-1">
					<button
						class="bottom-10 h-16 w-16 cursor-pointer rounded-full
                        bg-blue-600 text-2xl font-bold text-white hover:brightness-80"
						onclick={() => reportHazard('puddle')}
						title="Puddle"
					>
						<i class="ti ti-droplet"></i>
					</button>
					<span class="text-white">Puddle</span>
				</div>
				<div class="flex flex-col items-center justify-center gap-1">
					<button
						class="bottom-10 h-16 w-16 cursor-pointer rounded-full
                        bg-red-600 text-2xl font-bold text-white hover:brightness-80"
						onclick={() => reportHazard('crack')}
						title="Crack"
					>
						<i class="ti ti-alert-triangle"></i>
					</button>
					<span class="text-white">Crack</span>
				</div>
			{/if}
			<div class="absolute right-6 bottom-16">
				<div
					class="-border-l-2 -border-r-2 -border-b-2 -border-t-2
                            h-0 w-0
                            border-8 border-t-gray-700
                            border-r-transparent border-b-transparent border-l-transparent"
				></div>
			</div>
		</div>
	{/if}

	<button
		class="h-16 w-16 cursor-pointer rounded-full bg-blue-600
                text-2xl font-bold text-white hover:brightness-80"
		onclick={reportClick}
		title="Report"
	>
		<i class="ti ti-alert-triangle"></i>
	</button>
</div>
