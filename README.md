## About
This website is the implementation of a ConvNeXt model trained on a dataset of 20,000+ pictures of dogs. The DogBreed AI site allows you to upload a pictore of a dog (or dogs) and have the model determine the breed of the dog. See the "Learn more" tab on the site for more information. The frontend is hosted on netlify, while the backend and the model are hosted on hugging face spaces. Check it out yourself: https://dogbreed-ai.netlify.app

see the "training_source_code" folder to see the process of teaching the model.

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`
