from client import GitHubClient
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
resp = c.get('/settings/profile')
soup = BeautifulSoup(resp.text, 'html.parser')

# Check all avatar images
imgs = soup.select('img.avatar')
print(f"Found {len(imgs)} img.avatar elements")
for img in imgs[:5]:
    src = img.get('src', '')
    print(f"  src: {src[:150]}")

# Check the specific selectors used in step_avatar
avatar_img = soup.select_one('.avatar-upload img.avatar, .js-upload-avatar-image img.avatar')
print(f"\n.avatar-upload/.js-upload-avatar-image selector: {avatar_img}")

avatar_img2 = soup.select_one("img.avatar[src*='avatars.githubusercontent.com']")
print(f"avatars.githubusercontent.com selector: {avatar_img2 is not None}")
if avatar_img2:
    src = avatar_img2.get('src', '')
    print(f"  src: {src[:150]}")
    print(f"  has u=: {'u=' in src}")

# Check file-attachment element
fa = soup.find('file-attachment', class_='js-upload-avatar-image')
print(f"\nfile-attachment found: {fa is not None}")
if fa:
    print(f"  owner_id: {fa.get('data-alambic-owner-id')}")
