-- Dumps the real R15 for the Blender side (r15_rig.py): every part's size and rest CFrame relative to the root, every
-- joint's parent and C0/C1, the floor, and each part's real mesh when Studio lets EditableMesh read it.
-- A reply over about 100k characters is cut short, so ONLY = "" returns the rig and each part's mesh id, and ONLY = "<part>" one mesh.
-- Run: python pipeline.py dump   (writes <project>/animation/r15_rig.json)
local ONLY = ""
local Players = game:GetService("Players")
local AssetService = game:GetService("AssetService")
local HttpService = game:GetService("HttpService")

for _, old in workspace:GetChildren() do
	if old.Name == "AnimDumpRig" then
		old:Destroy()
	end
end
local rig = Players:CreateHumanoidModelFromDescription(Instance.new("HumanoidDescription"), Enum.HumanoidRigType.R15)
rig.Name = "AnimDumpRig"
rig:PivotTo(CFrame.new(0, 200, 0))
rig.Parent = workspace
local humanoid = rig:FindFirstChildOfClass("Humanoid") :: Humanoid
humanoid:BuildRigFromAttachments()

local root = rig:FindFirstChild("HumanoidRootPart") :: BasePart
local function cf(c: CFrame): { number }
	return { c:GetComponents() }
end

local parts, joints, meshes = {}, {}, {}
for _, item in rig:GetDescendants() do
	if item:IsA("BasePart") then
		parts[item.Name] = { Size = { item.Size.X, item.Size.Y, item.Size.Z }, CFrame = cf(root.CFrame:ToObjectSpace(item.CFrame)) }
		if item:IsA("MeshPart") and item.Name == ONLY then
			local ok, mesh = pcall(function()
				return AssetService:CreateEditableMeshAsync(Content.fromUri(item.MeshId))
			end)
			if ok and mesh then
				local ids, positions, index = mesh:GetVertices(), {}, {}
				for i, id in ids do
					index[id] = i - 1
					local p = mesh:GetPosition(id)
					table.insert(positions, math.round(p.X * 1e4) / 1e4)
					table.insert(positions, math.round(p.Y * 1e4) / 1e4)
					table.insert(positions, math.round(p.Z * 1e4) / 1e4)
				end
				local faces = {}
				for _, face in mesh:GetFaces() do
					for _, id in mesh:GetFaceVertices(face) do
						table.insert(faces, index[id])
					end
				end
				-- the mesh's own bounds, so the importer can fit it to the part's Size (a part scales its mesh to fill it)
				meshes[item.Name] = { Verts = positions, Tris = faces, MeshSize = { item.MeshSize.X, item.MeshSize.Y, item.MeshSize.Z } }
				mesh:Destroy()
			else
				meshes[item.Name] = { Error = tostring(mesh) }
			end
		end
	elseif item:IsA("Motor6D") and item.Part0 and item.Part1 then
		joints[item.Part1.Name] = { Name = item.Name, Parent = item.Part0.Name, C0 = cf(item.C0), C1 = cf(item.C1), Kind = "Motor6D" }
	elseif item:IsA("AnimationConstraint") and item.Attachment0 and item.Attachment1 then
		local a0, a1 = item.Attachment0, item.Attachment1
		joints[a1.Parent.Name] = { Name = item.Name, Parent = a0.Parent.Name, C0 = cf(a0.CFrame), C1 = cf(a1.CFrame), Kind = "AnimationConstraint" }
	end
end

local rootPart = rig:FindFirstChild("HumanoidRootPart") :: BasePart
local out = {
	Parts = parts,
	Joints = joints,
	Meshes = meshes,
	HipHeight = humanoid.HipHeight,
	RootSize = { rootPart.Size.X, rootPart.Size.Y, rootPart.Size.Z },
	Floor = -(rootPart.Size.Y / 2 + humanoid.HipHeight),
}
rig:Destroy()
return HttpService:JSONEncode(if ONLY ~= "" then meshes[ONLY] else out)
