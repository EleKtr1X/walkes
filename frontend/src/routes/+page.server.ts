import type { PageServerLoad } from './$types';
import { PUBLIC_SERVER_URL } from '$env/static/public';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${PUBLIC_SERVER_URL}/segments`);
	const json = await res.json();
	return json;
};
