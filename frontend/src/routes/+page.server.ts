import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch('https://walkes-backend.vercel.app/segments');
	const json = await res.json();
	return json;
};
